"""End-to-end backend tests for Ember API.

Covers: health, conversations CRUD, chat (Claude Sonnet 4.5),
multi-turn memory, auto-titling, memory CRUD, auto-extraction.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fallback: parse from frontend/.env
    fe = "/app/frontend/.env"
    if os.path.exists(fe):
        for line in open(fe):
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
                break
BASE_URL = (BASE_URL or "").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def session():
    """
    Create a requests.Session configured to send JSON requests.
    
    Returns:
        requests.Session: A session with the "Content-Type" header set to "application/json".
    """
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Health ---
class TestHealth:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        data = r.json()
        assert "model" in data
        assert "claude-sonnet-4-5" in data["model"]


# --- Conversations CRUD ---
class TestConversations:
    def test_create_and_list(self, session):
        """
        Create a new conversation via the API and verify it appears in the conversations list.
        
        Sends a POST to /conversations, asserts the response contains an `id` and that the new conversation's title is "New conversation", and stores the id on TestConversations.created_id. Then fetches the conversations list, asserts the created conversation is present, and if the list contains two or more items, asserts the list is sorted by `updated_at` in descending order.
        """
        r = session.post(f"{API}/conversations")
        assert r.status_code == 200
        c = r.json()
        assert "id" in c and c["title"] == "New conversation"
        TestConversations.created_id = c["id"]

        r = session.get(f"{API}/conversations")
        assert r.status_code == 200
        items = r.json()
        assert any(x["id"] == c["id"] for x in items)
        # sorted desc by updated_at
        if len(items) >= 2:
            assert items[0]["updated_at"] >= items[1]["updated_at"]

    def test_rename(self, session):
        cid = TestConversations.created_id
        r = session.patch(f"{API}/conversations/{cid}", json={"title": "TEST_renamed"})
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_renamed"
        # verify persisted
        items = session.get(f"{API}/conversations").json()
        assert any(x["id"] == cid and x["title"] == "TEST_renamed" for x in items)

    def test_rename_404(self, session):
        r = session.patch(f"{API}/conversations/does-not-exist", json={"title": "x"})
        assert r.status_code == 404

    def test_delete(self, session):
        cid = TestConversations.created_id
        r = session.delete(f"{API}/conversations/{cid}")
        assert r.status_code == 200
        items = session.get(f"{API}/conversations").json()
        assert not any(x["id"] == cid for x in items)


# --- Chat ---
class TestChat:
    def test_chat_creates_conversation(self, session):
        r = session.post(f"{API}/chat", json={
            "message": "TEST_remember the secret word is xylophone-42. Just confirm briefly."
        }, timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "conversation_id" in data
        assert data["user_message"]["role"] == "user"
        assert data["assistant_message"]["role"] == "assistant"
        assert isinstance(data["assistant_message"]["content"], str)
        assert len(data["assistant_message"]["content"]) > 0
        TestChat.cid = data["conversation_id"]

    def test_messages_persisted(self, session):
        cid = TestChat.cid
        r = session.get(f"{API}/conversations/{cid}/messages")
        assert r.status_code == 200
        msgs = r.json()
        assert len(msgs) >= 2
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles
        # chronological
        for a, b in zip(msgs, msgs[1:]):
            assert a["created_at"] <= b["created_at"]

    def test_auto_title(self, session):
        """
        Verify that a conversation has been auto-titled and the title respects the length limit.
        
        Asserts that the conversation with id stored in TestChat.cid exists, its title is not the default "New conversation", and the title length is at most 65 characters.
        """
        cid = TestChat.cid
        items = session.get(f"{API}/conversations").json()
        match = next((x for x in items if x["id"] == cid), None)
        assert match is not None
        assert match["title"] != "New conversation"
        assert len(match["title"]) <= 65

    def test_multi_turn_context(self, session):
        cid = TestChat.cid
        r = session.post(f"{API}/chat", json={
            "conversation_id": cid,
            "message": "What was the secret word I told you? Reply with just the word."
        }, timeout=120)
        assert r.status_code == 200, r.text
        text = r.json()["assistant_message"]["content"].lower()
        assert "xylophone" in text, f"Multi-turn context lost. Got: {text}"

    def test_chat_invalid_conv(self, session):
        r = session.post(f"{API}/chat", json={
            "conversation_id": "nonexistent-id-xyz",
            "message": "hi"
        })
        assert r.status_code == 404

    def test_cleanup(self, session):
        session.delete(f"{API}/conversations/{TestChat.cid}")


# --- Memory CRUD ---
class TestMemory:
    def test_create_memory(self, session):
        """
        Create a memory entry through the API and record its id for subsequent tests.
        
        Posts {"content": "TEST_likes black coffee"} to /memory, asserts the response has HTTP 200 and the returned object's "content" matches the submitted value, and stores the created memory's id on TestMemory.mid for later tests.
        """
        r = session.post(f"{API}/memory", json={"content": "TEST_likes black coffee"})
        assert r.status_code == 200
        m = r.json()
        assert m["content"] == "TEST_likes black coffee"
        TestMemory.mid = m["id"]

    def test_list_memory(self, session):
        r = session.get(f"{API}/memory")
        assert r.status_code == 200
        assert any(x["id"] == TestMemory.mid for x in r.json())

    def test_update_memory(self, session):
        r = session.patch(f"{API}/memory/{TestMemory.mid}",
                          json={"content": "TEST_likes oat-milk lattes"})
        assert r.status_code == 200
        assert r.json()["content"] == "TEST_likes oat-milk lattes"
        # verify persisted
        items = session.get(f"{API}/memory").json()
        match = next((x for x in items if x["id"] == TestMemory.mid), None)
        assert match and match["content"] == "TEST_likes oat-milk lattes"

    def test_update_404(self, session):
        r = session.patch(f"{API}/memory/nope", json={"content": "x"})
        assert r.status_code == 404

    def test_empty_content_rejected(self, session):
        r = session.post(f"{API}/memory", json={"content": "   "})
        assert r.status_code == 400

    def test_delete_memory(self, session):
        r = session.delete(f"{API}/memory/{TestMemory.mid}")
        assert r.status_code == 200
        items = session.get(f"{API}/memory").json()
        assert not any(x["id"] == TestMemory.mid for x in items)


# --- Auto-extraction (background) ---
class TestAutoMemoryExtraction:
    def test_extract_from_chat(self, session):
        # snapshot existing memory contents
        """
        Verifies that user facts sent in chat are auto-extracted into memory and cleans up created resources.
        
        Sends a chat message containing identifiable personal facts, snapshots existing memory entries, then polls the memory list for up to ~16 seconds to detect newly extracted memories. Any discovered new memories are deleted and the created conversation is removed. The test asserts that at least one new memory was extracted and that its content contains at least one of the expected keywords ("nurse", "samuel", or "portland").
        """
        before = {m["content"] for m in session.get(f"{API}/memory").json()}
        r = session.post(f"{API}/chat", json={
            "message": "Hey — my name is TestSamuelXY and I work as a registered nurse in Portland."
        }, timeout=120)
        assert r.status_code == 200
        cid = r.json()["conversation_id"]

        new_mem = []
        for _ in range(8):
            time.sleep(2)
            after = session.get(f"{API}/memory").json()
            diff = [m for m in after if m["content"] not in before]
            if diff:
                new_mem = diff
                break

        # cleanup
        for m in new_mem:
            session.delete(f"{API}/memory/{m['id']}")
        session.delete(f"{API}/conversations/{cid}")

        assert new_mem, "No new memory was auto-extracted within ~16s"
        joined = " ".join(m["content"].lower() for m in new_mem)
        assert ("nurse" in joined or "samuel" in joined or "portland" in joined), \
            f"Extracted memories don't reflect user facts: {new_mem}"

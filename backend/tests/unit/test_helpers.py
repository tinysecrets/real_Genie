import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

import backend.server as server

from fakes import _FakeCollection, _FakeDB, _FakeRequest


@pytest.fixture
def fakedb(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(server, "db", db)
    yield db


USER = {
    "user_id": "u1",
    "email": "alice@example.com",
    "name": "Alice",
    "created_at": "2024-01-01T00:00:00+00:00",
}


# ---------- now_iso ----------
def test_now_iso_is_utc():
    dt = datetime.fromisoformat(server.now_iso())
    assert dt.tzinfo is not None
    assert dt.tzinfo.utcoffset(None).total_seconds() == 0


# ---------- CSRF origin guard ----------
def test_no_origin_allowed():
    assert server._origin_allowed(_FakeRequest(origin=None)) is True


def test_allowlisted_origin_allowed():
    assert server._origin_allowed(_FakeRequest(origin="http://localhost:3000")) is True


def test_same_host_allowed():
    assert server._origin_allowed(_FakeRequest(origin="http://localhost:8000")) is True


def test_foreign_origin_blocked():
    assert server._origin_allowed(_FakeRequest(origin="https://evil.example", hostname="localhost", port=8000)) is False


def test_same_host_wrong_port_blocked():
    assert server._origin_allowed(_FakeRequest(origin="http://localhost:9999", hostname="localhost", port=8000)) is False


# ---------- auth ----------
async def test_auth_requires_token(fakedb):
    with pytest.raises(HTTPException) as ei:
        await server.get_user_from_request(_FakeRequest(), authorization=None)
    assert ei.value.status_code == 401


async def test_auth_rejects_expired_session(fakedb):
    fakedb.user_sessions = _FakeCollection(
        [{"session_token": "tok", "user_id": "u1", "expires_at": "2020-01-01T00:00:00+00:00"}]
    )
    with pytest.raises(HTTPException) as ei:
        await server.get_user_from_request(_FakeRequest(cookies={"session_token": "tok"}), authorization=None)
    assert ei.value.status_code == 401


async def test_auth_rejects_invalid_token(fakedb):
    fakedb.user_sessions = _FakeCollection([])
    with pytest.raises(HTTPException) as ei:
        await server.get_user_from_request(_FakeRequest(cookies={"session_token": "nope"}), authorization=None)
    assert ei.value.status_code == 401


async def test_auth_returns_user(fakedb):
    fakedb.user_sessions = _FakeCollection(
        [{"session_token": "tok", "user_id": "u1", "expires_at": "2999-01-01T00:00:00+00:00"}]
    )
    fakedb.users = _FakeCollection([dict(USER)])
    user = await server.get_user_from_request(_FakeRequest(cookies={"session_token": "tok"}), authorization=None)
    assert user.email == "alice@example.com"


async def test_auth_supports_bearer_header(fakedb):
    fakedb.user_sessions = _FakeCollection(
        [{"session_token": "tok", "user_id": "u1", "expires_at": "2999-01-01T00:00:00+00:00"}]
    )
    fakedb.users = _FakeCollection([dict(USER)])
    user = await server.get_user_from_request(_FakeRequest(), authorization="Bearer tok")
    assert user.user_id == "u1"


# ---------- persona ----------
async def test_get_persona_defaults(fakedb):
    assert await server.get_persona("u1") == server.DEFAULT_PERSONA


async def test_get_persona_saved(fakedb):
    fakedb.user_settings = _FakeCollection([{"user_id": "u1", "persona": "Crisp."}])
    assert await server.get_persona("u1") == "Crisp."


# ---------- system prompt ----------
async def test_build_system_prompt_uses_memories_and_persona(fakedb):
    fakedb.memories = _FakeCollection(
        [{"user_id": "u1", "content": "Likes black tea", "created_at": "2024-01-01T00:00:00+00:00"}]
    )
    fakedb.user_settings = _FakeCollection([{"user_id": "u1", "persona": "Blunt and kind."}])
    user = server.User(**USER)
    prompt = await server.build_system_prompt(user)
    assert "Likes black tea" in prompt
    assert "Blunt and kind." in prompt
    assert "Alice" in prompt


# ---------- memory extraction ----------
async def test_extract_memories_inserts_and_dedupes(fakedb, monkeypatch):
    async def fake_ollama(system, prompt):
        return '["Likes black tea", "Has a dog"]'

    monkeypatch.setattr(server, "ollama_chat", fake_ollama)
    fakedb.memories = _FakeCollection([{"user_id": "u1", "content": "Likes black tea"}])

    await server.extract_memories_async("u1", "I like tea", "Nice!")

    contents = [d["content"] for d in await fakedb.memories.find({}).to_list(100)]
    assert "Has a dog" in contents
    assert contents.count("Likes black tea") == 1


async def test_extract_memories_ignores_non_json(fakedb, monkeypatch):
    async def fake_ollama(system, prompt):
        return "sorry, no facts here"

    monkeypatch.setattr(server, "ollama_chat", fake_ollama)
    await server.extract_memories_async("u1", "hi", "hello")
    assert await fakedb.memories.find({}).to_list(100) == []
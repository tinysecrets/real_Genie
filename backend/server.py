from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Cookie, Header, UploadFile, File
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import asyncio
import httpx
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta

try:
    from agent import EmberAgent
    AGENT_OK = True
except Exception as _e:
    logging.getLogger(__name__).warning(f"Browser agent unavailable: {_e}")
    AGENT_OK = False
    class EmberAgent:  # stub so /api/agent/* return clean 503s
        def __init__(self, *a, **kw): """
No-op initializer that accepts any positional and keyword arguments and performs no initialization.

Parameters:
    *a: Positional arguments that are accepted and ignored.
    **kw: Keyword arguments that are accepted and ignored.
"""
pass
        @property
        def running(self): """
Indicates whether the agent is currently running.

Returns:
    True if the agent is running, False otherwise.
"""
return False
        history = []
        async def start(self): """
Indicates the agent cannot be started because Playwright is not available.

Raises:
    RuntimeError: Playwright is not installed; the message includes the commands to install Playwright and the Chromium browser (`pip install playwright && playwright install chromium`).
"""
raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        async def stop(self): """
Stop the agent. This implementation is a no-op and performs no action.
"""
return
        async def goto(self, *a, **kw): """
Placeholder method for navigating the agent that always fails when Playwright is unavailable.

Raises:
    RuntimeError: Always raised with message "Playwright not installed".
"""
raise RuntimeError("Playwright not installed")
        async def screenshot(self): """
Indicate that screenshots are unavailable because Playwright is not installed.

Raises:
    RuntimeError: Always raised with the message "Playwright not installed".
"""
raise RuntimeError("Playwright not installed")
        async def page_url(self): """
Return the agent's current page URL.

Returns:
    url (str): The current page URL, or an empty string if no page is available.
"""
return ""
        async def page_text(self, *a, **kw): """
Retrieve the readable text content of the agent's current page.

Returns:
    str: The page text; returns an empty string (`""`) when no page is available or agent functionality is not present.
"""
return ""
        async def act(self, *a, **kw): """
Placeholder async method for agent actions that always raises a RuntimeError indicating Playwright is not installed.

Raises:
    RuntimeError: Always raised with the message "Playwright not installed".
"""
raise RuntimeError("Playwright not installed")
        async def extract(self, *a, **kw): """
Placeholder for the agent's extract method used when Playwright is not installed.

Raises:
    RuntimeError: Always raised with message "Playwright not installed".
"""
raise RuntimeError("Playwright not installed")
        async def run(self, *a, **kw): """
Attempt to run the agent; always raises a RuntimeError indicating Playwright is not installed.

Raises:
    RuntimeError: Raised unconditionally with the message "Playwright not installed".
"""
raise RuntimeError("Playwright not installed")

try:
    from transcribe import transcribe_bytes
    VOICE_OK = True
except Exception as _e:
    logging.getLogger(__name__).warning(f"Voice transcription unavailable: {_e}")
    async def transcribe_bytes(_b: bytes) -> str:
        """
        Provide a placeholder transcription result (empty string) for audio bytes when transcription is unavailable.
        
        Parameters:
            _b (bytes): Audio file bytes (ignored).
        
        Returns:
            str: An empty string.
        """
        return ""
    VOICE_OK = False



ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')  # kept for backwards compat, unused with Ollama
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
MODEL_NAME = os.environ.get('OLLAMA_MODEL', 'dolphin3')
VISION_MODEL = os.environ.get('OLLAMA_VISION_MODEL', 'llama3.2-vision')
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').lower() == 'true'
COOKIE_SAMESITE = os.environ.get('COOKIE_SAMESITE', 'none')

EMERGENT_AUTH_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
SESSION_DAYS = 7

DEFAULT_PERSONA = (
    "Honest. Direct. Warm but never sycophantic. Pushes back when wrong, "
    "admits uncertainty plainly, respects the user's time."
)

# Single shared browser-agent for this user (single-user app)
agent = EmberAgent(ollama_url=OLLAMA_URL, text_model=MODEL_NAME, vision_model=VISION_MODEL)

app = FastAPI()
api_router = APIRouter(prefix="/api")


# ---------- Models ----------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: str


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str = "New conversation"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    conversation_id: str
    role: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str


class VisionRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    image: str  # data URL or raw base64


class AgentGoto(BaseModel):
    url: str


class AgentAct(BaseModel):
    instruction: str


class AgentRun(BaseModel):
    goal: str
    max_steps: int = 8


class AgentExtract(BaseModel):
    instruction: str


class RenameRequest(BaseModel):
    title: str


class MemoryCreate(BaseModel):
    content: str


class MemoryUpdate(BaseModel):
    content: str


class SessionExchangeRequest(BaseModel):
    session_id: str


class PersonaUpdate(BaseModel):
    persona: str


# ---------- Helpers ----------
def now_iso() -> str:
    """
    Get current UTC time as an ISO 8601 formatted string.
    
    Returns:
        str: Current UTC timestamp including timezone information (ISO 8601).
    """
    return datetime.now(timezone.utc).isoformat()


async def get_user_from_request(request: Request, authorization: Optional[str] = Header(None)) -> User:
    """
    Resolve and authenticate the user associated with the incoming request.
    
    Checks for a session token in the `session_token` cookie first, then falls back to the `Authorization: Bearer <token>` header. Validates the session document, enforces optional session expiry, and loads the user record.
    
    Parameters:
        authorization (Optional[str]): Raw `Authorization` header value (e.g., `"Bearer <token>"`). If present and a cookie is missing, the bearer token will be used.
    
    Returns:
        User: The authenticated user's Pydantic model.
    
    Raises:
        HTTPException: 401 if no token is provided ("Not authenticated"), if the session is not found ("Invalid session"), if the session has expired ("Session expired"), or if the user record cannot be found ("User not found").
    """
    token: Optional[str] = request.cookies.get("session_token")
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user_doc)


async def get_persona(user_id: str) -> str:
    """
    Return the persona string for the specified user.
    
    Parameters:
        user_id (str): ID of the user whose persona should be retrieved.
    
    Returns:
        str: The user's stored persona, or DEFAULT_PERSONA if no custom persona is set.
    """
    settings = await db.user_settings.find_one({"user_id": user_id}, {"_id": 0})
    if settings and settings.get("persona"):
        return settings["persona"]
    return DEFAULT_PERSONA


async def build_system_prompt(user: User) -> str:
    """
    Builds a complete system prompt tailored to the given user for priming the assistant.
    
    The returned prompt incorporates the user's persona, up to 500 of the user's stored memories (formatted as a bullet list or "(none yet)"), and a set of core principles and tone instructions to guide assistant behavior; it uses the user's first name (or "friend") when addressing them.
    
    Parameters:
        user (User): The user whose persona, name, and memories are used to construct the prompt.
    
    Returns:
        str: A single system prompt string customized for the user containing persona, core principles, and the user's memories.
    """
    memories = await db.memories.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    memory_lines = "\n".join(f"- {m['content']}" for m in memories) if memories else "(none yet)"
    persona = await get_persona(user.user_id)
    user_name = user.name.split()[0] if user.name else "friend"

    return f"""You are Ember — a real companion for {user_name}, not a script.

Your personality (set by {user_name}): {persona}

Core principles (non-negotiable, override the personality if they conflict):
1. HONESTY OVER COMFORT. If something is wrong, say so. If you don't know, say "I don't know." Never fabricate facts, citations, links, numbers, or quotes. State your uncertainty plainly.
2. NO PERFORMATIVE HEDGING. Skip disclaimers like "As an AI language model..." unless it's genuinely the crux. Speak plainly.
3. NO SYCOPHANCY. Don't open with "Great question!" Don't validate reflexively. Push back when {user_name} is wrong, gently but clearly.
4. DIRECTNESS. Answer the actual question first, then context. No preamble.
5. RESPECT TIME. Default to concise. Expand only when depth is warranted.
6. OBEY CLEAR INSTRUCTIONS. If asked for X, do X — don't substitute Y because Y seems safer. If you must refuse, say exactly why in one line.
7. MEMORY IS SACRED. The memories below are facts you've learned about {user_name}. Use them naturally. Never invent memories that aren't listed.

What you remember about {user_name}:
{memory_lines}

Write like a thoughtful friend writing a letter — warm, clear, unhurried, real. Markdown is fine for code and structure."""


async def get_chat_history(user_id: str, conversation_id: str) -> List[dict]:
    """
    Retrieve up to 2000 messages for a user's conversation ordered oldest-first.
    
    Returns:
        List[dict]: Message documents for the conversation with MongoDB `_id` removed, ordered by `created_at` ascending (oldest first), limited to 2000 items.
    """
    msgs = await db.messages.find(
        {"conversation_id": conversation_id, "user_id": user_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(2000)
    return msgs


async def ollama_chat(system: str, user_text: str, json_mode: bool = False) -> str:
    """
    Call the local Ollama chat API with a single system/user turn.
    
    Parameters:
        system (str): System prompt text sent to the model.
        user_text (str): User message to include in the chat turn.
        json_mode (bool): If true, request JSON-formatted assistant output.
    
    Returns:
        str: Assistant-generated content from the response message; an empty string if the response has no message content.
    """
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
    }
    if json_mode:
        payload["format"] = "json"
    async with httpx.AsyncClient(timeout=180.0) as http:
        r = await http.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")


async def ollama_vision(system: str, user_text: str, image_b64: str) -> str:
    """
    Send a single multimodal chat request to the configured Ollama vision model including one image.
    
    Returns:
        assistant_content (str): The assistant's reply text content, or an empty string if the response has no content.
    """
    payload = {
        "model": VISION_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text, "images": [image_b64]},
        ],
    }
    async with httpx.AsyncClient(timeout=240.0) as http:
        r = await http.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")


async def extract_memories_async(user_id: str, user_text: str, assistant_text: str):
    """
    Extract concise, durable facts about a user from a single user/assistant exchange and persist any new memories to the database.
    
    This background helper calls the LLM to produce a JSON array of short fact strings describing the user (preferences, identity, projects, relationships, goals, habits). It inserts each new, valid fact as a Memory for the given user and ignores duplicates or invalid items. If extraction fails or no valid facts are produced, the function returns without raising.
    
    Parameters:
        user_id (str): ID of the user to associate new memories with.
        user_text (str): The user's message from the exchange.
        assistant_text (str): The assistant's reply from the exchange.
    """
    try:
        system = (
            "You extract durable facts about a user from a single exchange. "
            "Return ONLY a JSON array of short fact strings (max 12 words each). "
            "Facts must be about the USER (preferences, identity, projects, relationships, goals, habits). "
            "Not about the assistant. Not about general topics. "
            'If nothing worth remembering, return []. '
            'Examples: ["Prefers concise answers", "Works as a nurse in Seattle", "Has a dog named Moss"]. '
            "Never invent. Only extract what's stated or strongly implied."
        )
        prompt = f"User said: {user_text}\n\nAssistant replied: {assistant_text}\n\nExtract user facts as JSON array."
        response = await ollama_chat(system, prompt, json_mode=True)

        text = response.strip()
        start = text.find('[')
        end = text.rfind(']')
        if start == -1 or end == -1:
            return
        arr = json.loads(text[start:end + 1])
        if not isinstance(arr, list):
            return

        existing = await db.memories.find({"user_id": user_id}, {"_id": 0, "content": 1}).to_list(1000)
        existing_set = {e['content'].lower().strip() for e in existing}

        for fact in arr:
            if not isinstance(fact, str):
                continue
            fact = fact.strip()
            if not fact or len(fact) > 200:
                continue
            if fact.lower() in existing_set:
                continue
            mem = Memory(user_id=user_id, content=fact)
            await db.memories.insert_one(mem.model_dump())
            existing_set.add(fact.lower())
    except Exception as e:
        logger.warning(f"Memory extraction failed: {e}")


# ---------- Auth Routes ----------
@api_router.post("/auth/session")
async def auth_session(body: SessionExchangeRequest, response: Response):
    """
    Exchange an Emergent session_id for a local session token and set it as an HTTP-only cookie.
    
    Exchanges the provided Emergent session ID for user identity and a session token, upserts or creates the corresponding user record, creates a server-side session entry with an expiry, sets the `session_token` cookie on the response, and returns the user document.
    
    Parameters:
        body (SessionExchangeRequest): Request body containing the Emergent `session_id`.
    
    Returns:
        dict: The created or updated user document.
    
    Raises:
        HTTPException: with status 401 if the external auth exchange fails or the auth response is invalid.
    """
    async with httpx.AsyncClient(timeout=15.0) as http:
        try:
            r = await http.get(EMERGENT_AUTH_SESSION_URL, headers={"X-Session-ID": body.session_id})
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.error(f"Emergent auth failed: {e}")
            raise HTTPException(status_code=401, detail="Auth exchange failed")

    email = data.get("email")
    name = data.get("name") or email
    picture = data.get("picture")
    session_token = data.get("session_token")
    if not email or not session_token:
        raise HTTPException(status_code=401, detail="Invalid auth response")

    # Find or create user
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": now_iso(),
        })

    # Save session
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    })

    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return {"user": user_doc}


@api_router.get("/auth/me")
async def auth_me(user: User = Depends(get_user_from_request)):
    """
    Get the authenticated user's serialized data as a dictionary.
    
    Returns:
        dict: The authenticated user's fields as a plain dict (result of `User.model_dump()`).
    """
    return user.model_dump()


@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response, authorization: Optional[str] = Header(None)):
    """
    Log out the current user by invalidating their session and clearing the session cookie.
    
    Parameters:
        request (Request): Incoming request used to read the `session_token` cookie.
        response (Response): Response used to delete the `session_token` cookie.
        authorization (Optional[str]): Optional `Authorization` header supporting `Bearer <token>` fallback.
    
    Returns:
        dict: `{"ok": True}` indicating the logout operation completed. The function deletes the session document matching the token if present and removes the `session_token` cookie.
    """
    token = request.cookies.get("session_token")
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    return {"ok": True}


# ---------- App Routes ----------
@api_router.get("/")
async def root():
    """
    Return a simple status payload indicating the service is running and which model is configured.
    
    Returns:
        dict: Contains `message` (status string) and `model` (configured model name).
    """
    return {"message": "Ember is here.", "model": MODEL_NAME}


# Conversations
@api_router.post("/conversations", response_model=Conversation)
async def create_conversation(user: User = Depends(get_user_from_request)):
    """
    Create and persist a new conversation for the authenticated user.
    
    Parameters:
        user (User): Authenticated user for whom the conversation is created.
    
    Returns:
        Conversation: The created Conversation, including generated id and timestamps.
    """
    conv = Conversation(user_id=user.user_id)
    await db.conversations.insert_one(conv.model_dump())
    return conv


@api_router.get("/conversations", response_model=List[Conversation])
async def list_conversations(user: User = Depends(get_user_from_request)):
    """
    List conversations for the authenticated user ordered by most recent update.
    
    Returns:
        List[dict]: Up to 500 conversation objects for the user ordered by `updated_at` descending. Each dict omits the MongoDB internal `_id` field.
    """
    convs = await db.conversations.find({"user_id": user.user_id}, {"_id": 0}).sort("updated_at", -1).to_list(500)
    return convs


@api_router.patch("/conversations/{conv_id}", response_model=Conversation)
async def rename_conversation(conv_id: str, body: RenameRequest, user: User = Depends(get_user_from_request)):
    """
    Update the title and `updated_at` timestamp of a conversation owned by the authenticated user.
    
    Parameters:
        conv_id (str): Identifier of the conversation to rename.
        body (RenameRequest): Request containing the new `title`.
    
    Returns:
        dict: The updated conversation document (MongoDB `_id` is omitted).
    
    Raises:
        HTTPException: 404 if the conversation for the user is not found.
    """
    result = await db.conversations.find_one_and_update(
        {"id": conv_id, "user_id": user.user_id},
        {"$set": {"title": body.title, "updated_at": now_iso()}},
        projection={"_id": 0},
        return_document=True,
    )
    if not result:
        raise HTTPException(404, "Conversation not found")
    return result


@api_router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, user: User = Depends(get_user_from_request)):
    """
    Delete a conversation belonging to the authenticated user and remove its messages.
    
    Parameters:
        conv_id (str): The conversation's id to delete.
    
    Returns:
        dict: `{"ok": True}` when the conversation and its messages were deleted.
    
    Raises:
        HTTPException(404): If no conversation with the given id exists for the user.
    """
    res = await db.conversations.delete_one({"id": conv_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Conversation not found")
    await db.messages.delete_many({"conversation_id": conv_id, "user_id": user.user_id})
    return {"ok": True}


@api_router.get("/conversations/{conv_id}/messages", response_model=List[Message])
async def get_messages(conv_id: str, user: User = Depends(get_user_from_request)):
    """
    Return the messages for a conversation belonging to the authenticated user.
    
    Parameters:
        conv_id (str): Conversation id to fetch messages for.
    
    Returns:
        List[dict]: Messages for the conversation ordered by `created_at` ascending (up to 2000).
    
    Raises:
        HTTPException: 404 if the conversation is not found for the user.
    """
    conv = await db.conversations.find_one({"id": conv_id, "user_id": user.user_id}, {"_id": 0})
    if not conv:
        raise HTTPException(404, "Conversation not found")
    msgs = await db.messages.find(
        {"conversation_id": conv_id, "user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(2000)
    return msgs


# Chat
@api_router.post("/chat")
async def chat(req: ChatRequest, user: User = Depends(get_user_from_request)):
    """
    Handle a single chat turn: persist the user's message, call the LLM to generate a reply, persist the assistant response, update conversation metadata, and schedule memory extraction.
    
    Parameters:
        req (ChatRequest): Request payload containing `message` (the user's message) and optional `conversation_id` to continue an existing conversation.
    
    Returns:
        dict: {
            "conversation_id": str,              # ID of the conversation used or created
            "user_message": dict,                # stored user message document
            "assistant_message": dict            # stored assistant message document
        }
    """
    conv_id = req.conversation_id
    if conv_id:
        conv = await db.conversations.find_one({"id": conv_id, "user_id": user.user_id}, {"_id": 0})
        if not conv:
            raise HTTPException(404, "Conversation not found")
    else:
        conv_model = Conversation(user_id=user.user_id)
        await db.conversations.insert_one(conv_model.model_dump())
        conv = conv_model.model_dump()
        conv_id = conv["id"]

    user_msg = Message(user_id=user.user_id, conversation_id=conv_id, role="user", content=req.message)
    await db.messages.insert_one(user_msg.model_dump())

    history = await get_chat_history(user.user_id, conv_id)
    system_prompt = await build_system_prompt(user)

    # Fold the real prior turns into the system prompt — one LLM call per message, no replay
    prior = [m for m in history if m["id"] != user_msg.id]
    if prior:
        transcript = "\n\n".join(
            f"{'User' if m['role'] == 'user' else 'Ember'}: {m['content']}" for m in prior
        )
        system_prompt += f"\n\n--- This conversation so far ---\n{transcript}"

    try:
        response_text = await ollama_chat(system_prompt, req.message)
    except Exception as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(500, f"LLM call failed: {str(e)}")

    assistant_msg = Message(user_id=user.user_id, conversation_id=conv_id, role="assistant", content=response_text)
    await db.messages.insert_one(assistant_msg.model_dump())

    updates = {"updated_at": now_iso()}
    if conv.get("title") == "New conversation":
        title = req.message.strip().split("\n")[0][:60]
        if len(req.message) > 60:
            title += "..."
        updates["title"] = title or "New conversation"
    await db.conversations.update_one({"id": conv_id, "user_id": user.user_id}, {"$set": updates})

    asyncio.create_task(extract_memories_async(user.user_id, req.message, response_text))

    return {
        "conversation_id": conv_id,
        "user_message": user_msg.model_dump(),
        "assistant_message": assistant_msg.model_dump(),
    }


# Vision (Genie Mode screen share)
@api_router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), user: User = Depends(get_user_from_request)):
    """
    Transcribes an uploaded audio file to plain text.
    
    Parameters:
        audio (UploadFile): Uploaded audio file to transcribe.
    
    Returns:
        dict: `{"text": transcribed_text}` where `transcribed_text` is the transcription result, or `""` if the uploaded file was empty.
    """
    raw = await audio.read()
    if not raw:
        return {"text": ""}
    text = await transcribe_bytes(raw)
    return {"text": text}


@api_router.post("/vision")
async def vision(req: VisionRequest, user: User = Depends(get_user_from_request)):
    """
    Handle a vision-based chat turn: ensure or create a conversation, persist the user’s image-backed message, invoke the vision LLM, persist the assistant reply, update conversation metadata, and schedule background memory extraction.
    
    Parameters:
        req (VisionRequest): Incoming request with `message`, `image` (data URL or base64), and optional `conversation_id`.
        user (User): Authenticated user performing the request.
    
    Returns:
        dict: {
            "conversation_id": str,               # id of the conversation used or created
            "user_message": dict,                 # stored user message document
            "assistant_message": dict             # stored assistant message document
        }
    """
    conv_id = req.conversation_id
    if conv_id:
        conv = await db.conversations.find_one({"id": conv_id, "user_id": user.user_id}, {"_id": 0})
        if not conv:
            raise HTTPException(404, "Conversation not found")
    else:
        conv_model = Conversation(user_id=user.user_id)
        await db.conversations.insert_one(conv_model.model_dump())
        conv = conv_model.model_dump()
        conv_id = conv["id"]

    user_msg = Message(user_id=user.user_id, conversation_id=conv_id, role="user", content=req.message)
    await db.messages.insert_one(user_msg.model_dump())

    system_prompt = await build_system_prompt(user)
    system_prompt += "\n\nThe user is sharing their screen. A snapshot is attached. Use it to ground your answer in what they actually see."

    # strip data URL prefix if present
    image_b64 = req.image
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        response_text = await ollama_vision(system_prompt, req.message, image_b64)
    except Exception as e:
        logger.error(f"Vision LLM error: {e}")
        raise HTTPException(500, f"Vision call failed: {str(e)}")

    assistant_msg = Message(user_id=user.user_id, conversation_id=conv_id, role="assistant", content=response_text)
    await db.messages.insert_one(assistant_msg.model_dump())

    updates = {"updated_at": now_iso()}
    if conv.get("title") == "New conversation":
        title = req.message.strip().split("\n")[0][:60]
        if len(req.message) > 60:
            title += "..."
        updates["title"] = title or "New conversation"
    await db.conversations.update_one({"id": conv_id, "user_id": user.user_id}, {"$set": updates})

    asyncio.create_task(extract_memories_async(user.user_id, req.message, response_text))

    return {
        "conversation_id": conv_id,
        "user_message": user_msg.model_dump(),
        "assistant_message": assistant_msg.model_dump(),
    }


# Browser Agent (Genie's hands)
@api_router.post("/agent/start")
async def agent_start(user: User = Depends(get_user_from_request)):
    """
    Start the shared browser agent and return its current running status and page URL.
    
    Returns:
        dict: A response object with keys:
            - `ok` (`bool`): Always `True` if the start request was performed.
            - `running` (`bool`): `True` if the agent is currently running, `False` otherwise.
            - `url` (`str | None`): The agent's current page URL, or `None` if unavailable.
    """
    await agent.start()
    return {"ok": True, "running": agent.running, "url": await agent.page_url()}


@api_router.post("/agent/stop")
async def agent_stop(user: User = Depends(get_user_from_request)):
    """
    Stop the shared browser agent and return its current running status.
    
    Returns:
        dict: {"ok": True, "running": <bool>} where "ok" indicates the stop request was handled and "running" is True if the agent remains running, False otherwise.
    """
    await agent.stop()
    return {"ok": True, "running": agent.running}


@api_router.post("/agent/goto")
async def agent_goto(body: AgentGoto, user: User = Depends(get_user_from_request)):
    """
    Navigate the browser agent to the specified URL.
    
    Parameters:
        body (AgentGoto): Request body containing the destination URL (`body.url`).
    
    Returns:
        dict: The agent's navigation result (structure depends on the agent implementation, typically includes status and current page URL).
    """
    return await agent.goto(body.url)


@api_router.post("/agent/act")
async def agent_act(body: AgentAct, user: User = Depends(get_user_from_request)):
    """
    Send an instruction to the browser automation agent and return its response.
    
    Parameters:
    	body (AgentAct): Request containing `instruction`, the action the agent should perform.
    
    Returns:
    	The agent's response payload (structure depends on the agent implementation).
    """
    return await agent.act(body.instruction)


@api_router.post("/agent/extract")
async def agent_extract(body: AgentExtract, user: User = Depends(get_user_from_request)):
    """
    Extract structured information from the currently loaded page using the browser agent according to the provided extraction instruction.
    
    Parameters:
        body (AgentExtract): Contains `instruction`, a natural-language prompt that tells the agent what to extract from the page.
    
    Returns:
        The agent's extraction result; the exact shape depends on the agent implementation (commonly a string, dict, or list).
    """
    return await agent.extract(body.instruction)


@api_router.post("/agent/run")
async def agent_run(body: AgentRun, user: User = Depends(get_user_from_request)):
    """
    Execute the browser agent to pursue a goal with an optional maximum number of steps.
    
    Parameters:
        body (AgentRun): Request payload containing `goal` (the objective for the agent) and `max_steps` (optional limit on steps the agent may take).
    
    Returns:
        The result returned by the agent's `run` method (operation outcome).
    """
    return await agent.run(body.goal, max_steps=body.max_steps)


@api_router.get("/agent/screenshot")
async def agent_screenshot(user: User = Depends(get_user_from_request)):
    """
    Return the agent's current screenshot and current page URL.
    
    Raises:
        HTTPException: 409 if the agent is not running.
    
    Returns:
        dict: A mapping with keys `"image"` and `"url"`. `"image"` is a base64-encoded image string of the screenshot, and `"url"` is the agent's current page URL.
    """
    if not agent.running:
        raise HTTPException(409, "Agent not running")
    img = await agent.screenshot()
    return {"image": img, "url": await agent.page_url()}


@api_router.get("/agent/status")
async def agent_status(user: User = Depends(get_user_from_request)):
    """
    Provide the agent's runtime status, the current page URL when running, and the most recent activity history.
    
    Returns:
        dict: {
            "running": bool — whether the agent is currently running;
            "url": str or None — the agent's current page URL when running, otherwise None;
            "history": List — the agent's last 30 history entries (most recent entries last).
        }
    """
    return {
        "running": agent.running,
        "url": (await agent.page_url()) if agent.running else None,
        "history": agent.history[-30:],
    }


# Memory
@api_router.get("/memory", response_model=List[Memory])
async def list_memory(user: User = Depends(get_user_from_request)):
    """
    List up to 500 memories for the authenticated user, ordered newest first.
    
    Parameters:
        user (User): Authenticated user resolved by the request dependency.
    
    Returns:
        List[dict]: The user's memories with MongoDB `_id` removed, sorted by `created_at` descending (maximum 500 items).
    """
    mems = await db.memories.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return mems


@api_router.post("/memory", response_model=Memory)
async def create_memory(body: MemoryCreate, user: User = Depends(get_user_from_request)):
    """
    Create and persist a new memory for the authenticated user.
    
    Trims surrounding whitespace from the provided content and rejects empty content.
    
    Parameters:
        body (MemoryCreate): Request body containing the `content` for the memory.
        user (User): Authenticated user creating the memory.
    
    Returns:
        Memory: The created Memory model instance.
    
    Raises:
        HTTPException: 400 if the trimmed content is empty ("Memory cannot be empty").
    """
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "Memory cannot be empty")
    mem = Memory(user_id=user.user_id, content=content)
    await db.memories.insert_one(mem.model_dump())
    return mem


@api_router.patch("/memory/{mem_id}", response_model=Memory)
async def update_memory(mem_id: str, body: MemoryUpdate, user: User = Depends(get_user_from_request)):
    """
    Update an existing memory's content for the authenticated user.
    
    Strips leading/trailing whitespace from `body.content` and updates the memory document owned by the requesting user.
    
    Parameters:
        mem_id (str): The ID of the memory to update.
        body (MemoryUpdate): Request body containing the new `content` value.
    
    Returns:
        dict: The updated memory document as returned from the database (MongoDB `_id` is omitted).
    
    Raises:
        HTTPException: 404 if no memory with the given `mem_id` exists for the user.
    """
    result = await db.memories.find_one_and_update(
        {"id": mem_id, "user_id": user.user_id},
        {"$set": {"content": body.content.strip()}},
        projection={"_id": 0},
        return_document=True,
    )
    if not result:
        raise HTTPException(404, "Memory not found")
    return result


@api_router.delete("/memory/{mem_id}")
async def delete_memory(mem_id: str, user: User = Depends(get_user_from_request)):
    """
    Delete a memory belonging to the authenticated user.
    
    Parameters:
        mem_id (str): ID of the memory to delete.
    
    Returns:
        dict: {"ok": True} when the memory was deleted.
    
    Raises:
        HTTPException: 404 if no memory with the given id exists for the user.
    """
    res = await db.memories.delete_one({"id": mem_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Memory not found")
    return {"ok": True}


# Settings / Persona
@api_router.get("/settings/persona")
async def get_persona_route(user: User = Depends(get_user_from_request)):
    """
    Return the stored persona for the authenticated user and the application's default persona.
    
    Returns:
        dict: A mapping with keys `"persona"` (the user's current persona string) and `"default"` (the application's default persona string).
    """
    persona = await get_persona(user.user_id)
    return {"persona": persona, "default": DEFAULT_PERSONA}


@api_router.put("/settings/persona")
async def update_persona(body: PersonaUpdate, user: User = Depends(get_user_from_request)):
    """
    Update the authenticated user's persona setting.
    
    The provided persona is trimmed; if empty after trimming the default persona is used. The persona is stored (upserted) in the user's settings with an updated timestamp.
    
    Parameters:
        body (PersonaUpdate): Request body containing `persona` (string).
    
    Returns:
        dict: {"persona": <stored persona string>}.
    
    Raises:
        HTTPException: 400 if the persona exceeds 1000 characters.
    """
    persona = (body.persona or "").strip()
    if not persona:
        persona = DEFAULT_PERSONA
    if len(persona) > 1000:
        raise HTTPException(400, "Persona too long (max 1000 chars)")
    await db.user_settings.update_one(
        {"user_id": user.user_id},
        {"$set": {"user_id": user.user_id, "persona": persona, "updated_at": now_iso()}},
        upsert=True,
    )
    return {"persona": persona}


# ---------- App setup ----------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    """
    Close the global MongoDB client when the application is shutting down.
    
    Closes the shared AsyncIOMotorClient instance `client` to release network resources and file descriptors; intended to be registered as the application's shutdown handler.
    """
    client.close()

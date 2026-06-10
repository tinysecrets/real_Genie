"""
Ember Browser Agent — a tiny local Stagehand alternative.

Uses Playwright + a local Ollama vision/text model to:
  - act("click the login button")            — natural-language actions
  - extract("get the top 3 article titles")  — LLM-extracted structured data
  - run("buy a copy of dune", max_steps=20)  — autonomous multi-step goal
  - screenshot()                              — current page as JPEG

Design choices kept honest:
  - One agent session per backend process (single-user app, by design)
  - Headless by default; the frontend renders the live screenshot
  - Falls back gracefully if no vision model is available
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import Optional, Dict, Any, List

import httpx
from playwright.async_api import async_playwright, Browser, Page, Playwright

logger = logging.getLogger(__name__)


class EmberAgent:
    def __init__(self, ollama_url: str, text_model: str, vision_model: str):
        """
        Initialize an EmberAgent with Ollama configuration and reset internal browser/session state.
        
        Parameters:
            ollama_url (str): Base URL of the local Ollama chat endpoint (e.g. "http://localhost:11434").
            text_model (str): Model name to use for text-only LLM requests.
            vision_model (str): Model name to use when sending images to the LLM.
        
        Description:
            Stores the provided Ollama settings, initializes Playwright/browser/page handles to None, creates an asyncio.Lock to serialize lifecycle operations, and prepares an empty `history` list for human-readable event tracing.
        """
        self.ollama_url = ollama_url
        self.text_model = text_model
        self.vision_model = vision_model
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()
        self.history: List[Dict[str, Any]] = []   # human-readable trace

    # ---------- lifecycle ----------
    async def start(self):
        """
        Start a Playwright Chromium browser session and create a new page if one is not already running.
        
        Acquires the agent's internal lock to serialize lifecycle operations; if a page already exists the method returns immediately. On success it initializes internal Playwright/browser/page handles, resets the agent history, and records a "started" log entry.
        """
        async with self._lock:
            if self._page:
                return
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Ember Genie Agent)",
            )
            self._page = await ctx.new_page()
            self.history = []
            self._log("agent", "started")

    async def stop(self):
        """
        Stop the Playwright session and clear internal browser and page handles.
        
        Acquires the agent's internal lock, closes the browser if one exists, stops the Playwright driver, sets internal handles to None, and records a "stopped" event in the agent history.
        """
        async with self._lock:
            try:
                if self._browser:
                    await self._browser.close()
            finally:
                if self._pw:
                    await self._pw.stop()
                self._browser = None
                self._page = None
                self._pw = None
                self._log("agent", "stopped")

    async def _ensure(self):
        """
        Ensure a Playwright page session exists.
        
        If the agent does not currently have an active page, start the browser and create a new page by calling `start()`.
        """
        if not self._page:
            await self.start()

    # ---------- primitives ----------
    async def goto(self, url: str) -> Dict[str, Any]:
        """
        Navigate the managed browser page to the given URL.
        
        Parameters:
            url (str): Target URL or hostname; if the scheme is missing the function prepends "https://".
        
        Returns:
            dict: A result object with keys:
                - "ok" (bool): `True` on successful navigation.
                - "url" (str): The final page URL after navigation.
        """
        await self._ensure()
        if not re.match(r"^https?://", url):
            url = "https://" + url
        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self._log("goto", url)
        return {"ok": True, "url": self._page.url}

    async def screenshot(self) -> str:
        """
        Capture a JPEG screenshot of the current page and return it as a base64-encoded ASCII string.
        
        Returns:
            str: Base64-encoded ASCII string of the JPEG image bytes.
        """
        await self._ensure()
        png = await self._page.screenshot(type="jpeg", quality=70, full_page=False)
        return base64.b64encode(png).decode("ascii")

    async def page_text(self, max_chars: int = 4000) -> str:
        """
        Return the current page's body text truncated to at most `max_chars` characters.
        
        If reading the page body fails, returns an empty string.
        
        Parameters:
            max_chars (int): Maximum number of characters to include in the returned text.
        
        Returns:
            str: The page body text truncated to `max_chars` characters (or empty string on failure).
        """
        await self._ensure()
        try:
            text = await self._page.inner_text("body")
        except Exception:
            text = ""
        return text[:max_chars]

    async def page_url(self) -> str:
        """
        Get the current page's URL, ensuring the agent has an active page.
        
        Returns:
            str: The current page URL.
        """
        await self._ensure()
        return self._page.url

    # ---------- LLM helpers ----------
    async def _ollama(self, system: str, user: str, json_mode: bool = True, image_b64: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Send a chat request to the configured Ollama API and return the model's response content.
        
        If `model` is omitted, the vision model is used when `image_b64` is provided, otherwise the text model is used. When `image_b64` is present it is attached to the user message. If `json_mode` is True, the request asks the API to format its output as JSON.
        
        Parameters:
            system (str): System-level prompt to guide the model.
            user (str): User-level prompt or message content.
            json_mode (bool): If True, request JSON-formatted output from the model.
            image_b64 (Optional[str]): Base64-encoded image to include with the user message, if any.
            model (Optional[str]): Explicit model name to use; if omitted the method chooses a model based on `image_b64`.
        
        Returns:
            str: The model's message content from the Ollama response, or an empty string if missing.
        """
        model = model or (self.vision_model if image_b64 else self.text_model)
        msg: Dict[str, Any] = {"role": "user", "content": user}
        if image_b64:
            msg["images"] = [image_b64]
        payload = {
            "model": model,
            "stream": False,
            "messages": [{"role": "system", "content": system}, msg],
        }
        if json_mode:
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=240.0) as http:
            r = await http.post(f"{self.ollama_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            return (data.get("message") or {}).get("content", "")

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """
        Extracts and returns the first JSON object found inside a string, or an empty dict if none is found or parsing fails.
        
        Parameters:
            text (str): Input string that may contain a JSON object.
        
        Returns:
            dict: The parsed JSON object, or an empty dict if no valid JSON object could be extracted and parsed.
        """
        text = (text or "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {}
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return {}

    # ---------- act() — natural-language single action ----------
    async def act(self, instruction: str) -> Dict[str, Any]:
        """
        Ask the model to choose a single browser action that advances the given instruction, execute that action on the current page, and return the parsed action and its execution result.
        
        Parameters:
            instruction (str): Natural-language instruction describing the user's goal.
        
        Returns:
            dict: A dictionary with two keys:
                - "action": The parsed action object chosen by the model (e.g., one of
                  {"type":"click","text":...}, {"type":"fill","text":...,"value":...},
                  {"type":"press","key":...}, {"type":"goto","url":...},
                  {"type":"scroll","direction":"up"|"down"}, or {"type":"done","note":...}).
                - "result": The outcome of executing the action, typically a dict containing
                  an "ok" boolean and additional fields such as "reason" on failure or "done" on completion.
        """
        await self._ensure()
        img = await self.screenshot()
        body_text = await self.page_text(2500)
        system = (
            "You control a web browser. Pick ONE next action that best advances the user's instruction. "
            "Return ONLY a JSON object with one of these shapes:\n"
            '{"type":"click","text":"<visible label of element>"}\n'
            '{"type":"fill","text":"<visible label of input>","value":"<text to type>"}\n'
            '{"type":"press","key":"Enter"}\n'
            '{"type":"goto","url":"https://..."}\n'
            '{"type":"scroll","direction":"down"|"up"}\n'
            '{"type":"done","note":"<why you are done>"}\n'
            "Use the visible text the user would actually see."
        )
        user = f"Instruction: {instruction}\n\nCurrent URL: {self._page.url}\n\nVisible page text:\n{body_text}"
        raw = await self._ollama(system, user, json_mode=True, image_b64=img)
        action = self._parse_json(raw)
        result = await self._exec_action(action)
        self._log("act", instruction, action, result)
        return {"action": action, "result": result}

    # ---------- extract() — pull structured data ----------
    async def extract(self, instruction: str) -> Dict[str, Any]:
        """
        Extract structured information from the current page using the agent's LLM.
        
        The function sends the provided instruction plus the current page URL and visible text to the model and parses a single JSON object from the model response. If the requested data is a list, the result will use the key "items"; if it is a single value, the result will use the key "value". Returns an empty dict if no valid JSON object can be parsed.
        Parameters:
        	instruction (str): A natural-language prompt describing what information to extract from the page.
        
        Returns:
        	Dict[str, Any]: The parsed JSON object produced by the model (or `{}` on parse failure).
        """
        await self._ensure()
        body_text = await self.page_text(6000)
        system = (
            "Extract the requested information from the page text. "
            "Return ONLY a JSON object. If the answer is a list, key it 'items'. "
            "If a single value, key it 'value'. Never invent data."
        )
        user = f"Request: {instruction}\n\nPage URL: {self._page.url}\n\nPage text:\n{body_text}"
        raw = await self._ollama(system, user, json_mode=True)
        out = self._parse_json(raw)
        self._log("extract", instruction, out)
        return out

    # ---------- run() — autonomous goal loop ----------
    async def run(self, goal: str, max_steps: int = 8) -> Dict[str, Any]:
        """
        Iteratively executes actions chosen by the agent to pursue a natural-language goal.
        
        Calls `act(goal)` up to `max_steps` times, stopping early if an action with `"type": "done"` is returned. Each step's result is recorded; the agent pauses briefly between steps and logs the run before returning.
        
        Parameters:
        	goal (str): Natural-language goal or instruction the agent should pursue.
        	max_steps (int): Maximum number of action iterations to attempt.
        
        Returns:
        	result (Dict[str, Any]): A dictionary with:
        		- "goal" (str): The original goal.
        		- "steps" (List[Dict[str, Any]]): Ordered list of step results produced by `act`.
        		- "final_url" (str): The page URL at the end of the run.
        """
        await self._ensure()
        steps: List[Dict[str, Any]] = []
        for i in range(max_steps):
            step = await self.act(goal)
            steps.append(step)
            atype = (step.get("action") or {}).get("type")
            if atype == "done":
                break
            await asyncio.sleep(0.6)
        self._log("run", goal, {"steps": len(steps)})
        return {"goal": goal, "steps": steps, "final_url": self._page.url}

    # ---------- low-level action executor ----------
    async def _exec_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single high-level browser action described by the `action` mapping.
        
        The `action` parameter must be a dictionary containing a `"type"` key whose value is one of:
        - `"goto"`: requires `"url"` (string) to navigate the page.
        - `"click"`: uses `"text"` (string) to find and click a visible element.
        - `"fill"`: uses `"text"` (string) to identify an input (by label, placeholder, or textbox role) and `"value"` (string) to fill it.
        - `"press"`: optional `"key"` (string, defaults to `"Enter"`) to send via keyboard.
        - `"scroll"`: optional `"direction"` with value `"up"` to scroll up; any other value scrolls down.
        - `"done"`: optional `"note"` (string) to return as metadata.
        
        Parameters:
            action (Dict[str, Any]): Action specification as described above.
        
        Returns:
            Dict[str, Any]: Result object with at least `ok` (bool). On failure includes `reason` (string). For `"done"` actions includes `done` (True) and optional `note` (string).
        """
        if not action:
            return {"ok": False, "reason": "no action parsed"}
        t = action.get("type")
        try:
            if t == "goto":
                url = action.get("url") or ""
                if url:
                    await self.goto(url)
                    return {"ok": True}
                return {"ok": False, "reason": "no url"}
            if t == "click":
                target = action.get("text") or ""
                loc = self._page.get_by_text(target, exact=False).first
                await loc.click(timeout=8000)
                return {"ok": True}
            if t == "fill":
                target = action.get("text") or ""
                value = action.get("value") or ""
                # try by label, then placeholder, then role textbox
                try:
                    await self._page.get_by_label(target, exact=False).first.fill(value, timeout=4000)
                except Exception:
                    try:
                        await self._page.get_by_placeholder(target).first.fill(value, timeout=4000)
                    except Exception:
                        await self._page.get_by_role("textbox").first.fill(value, timeout=4000)
                return {"ok": True}
            if t == "press":
                key = action.get("key") or "Enter"
                await self._page.keyboard.press(key)
                return {"ok": True}
            if t == "scroll":
                dy = 600 if action.get("direction") != "up" else -600
                await self._page.evaluate(f"window.scrollBy(0, {dy})")
                return {"ok": True}
            if t == "done":
                return {"ok": True, "done": True, "note": action.get("note", "")}
            return {"ok": False, "reason": f"unknown type {t}"}
        except Exception as e:
            return {"ok": False, "reason": str(e)[:200]}

    # ---------- helpers ----------
    def _log(self, kind: str, *args):
        """
        Record an agent event in the in-memory history and emit an info log.
        
        Appends an entry {"kind": kind, "args": [...]} to the agent's history, truncating history to the most recent 200 entries, and logs the event via the module logger.
        
        Parameters:
            kind (str): A short label identifying the event type.
            *args: Additional context or values associated with the event.
        """
        entry = {"kind": kind, "args": [a for a in args]}
        self.history.append(entry)
        if len(self.history) > 200:
            self.history = self.history[-200:]
        logger.info(f"[agent] {kind}: {args}")

    @property
    def running(self) -> bool:
        """
        Whether the agent currently has an active Playwright page.
        
        Returns:
            bool: `True` if a Playwright page is present, `False` otherwise.
        """
        return self._page is not None

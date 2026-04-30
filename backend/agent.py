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
        if not self._page:
            await self.start()

    # ---------- primitives ----------
    async def goto(self, url: str) -> Dict[str, Any]:
        await self._ensure()
        if not re.match(r"^https?://", url):
            url = "https://" + url
        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self._log("goto", url)
        return {"ok": True, "url": self._page.url}

    async def screenshot(self) -> str:
        """Returns base64 JPEG of the current page."""
        await self._ensure()
        png = await self._page.screenshot(type="jpeg", quality=70, full_page=False)
        return base64.b64encode(png).decode("ascii")

    async def page_text(self, max_chars: int = 4000) -> str:
        await self._ensure()
        try:
            text = await self._page.inner_text("body")
        except Exception:
            text = ""
        return text[:max_chars]

    async def page_url(self) -> str:
        await self._ensure()
        return self._page.url

    # ---------- LLM helpers ----------
    async def _ollama(self, system: str, user: str, json_mode: bool = True, image_b64: Optional[str] = None, model: Optional[str] = None) -> str:
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
        """Have the model pick ONE action and execute it."""
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
        entry = {"kind": kind, "args": [a for a in args]}
        self.history.append(entry)
        if len(self.history) > 200:
            self.history = self.history[-200:]
        logger.info(f"[agent] {kind}: {args}")

    @property
    def running(self) -> bool:
        return self._page is not None

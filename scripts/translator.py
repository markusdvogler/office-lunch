"""Machine translation via MyMemory (free tier, no API key).

Docs: https://mymemory.translated.net/doc/spec.php

- GET https://api.mymemory.translated.net/get?q=<text>&langpair=de|en
- Anonymous free tier: ~5 000 chars/day, 500 chars per request.
- Response shape:
    {"responseData": {"translatedText": "..."},
     "responseStatus": 200, "matches": [...]}
- If we hit an error/quota the caller keeps the original text so the
  menu still renders — translation is a best-effort enrichment.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

_ENDPOINT = "https://api.mymemory.translated.net/get"
_MAX_LEN = 500       # per-request character limit
_MIN_INTERVAL = 0.2  # seconds between requests — be a good citizen
_TIMEOUT = 15


class Translator:
    """Simple cached MyMemory client. One instance per scraper run."""

    def __init__(self, session: Optional[requests.Session] = None,
                 email: Optional[str] = None,
                 logger: Optional[logging.Logger] = None):
        self.session = session or requests.Session()
        self.email = email  # doubles the quota if set, but not required
        self.logger = logger or logging.getLogger("translator")
        self._cache: dict[tuple[str, str, str], str] = {}
        self._last_call = 0.0
        self._disabled = False

    def translate(self, text: str, source: str, target: str) -> Optional[str]:
        text = (text or "").strip()
        if not text or source == target:
            return text or None
        if self._disabled:
            return None
        if len(text) > _MAX_LEN:
            # Too long for MyMemory's per-request limit; skip rather than
            # truncate silently — the source text remains available.
            return None
        key = (source, target, text)
        if key in self._cache:
            return self._cache[key]

        # Rate limit
        elapsed = time.monotonic() - self._last_call
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        params = {"q": text, "langpair": f"{source}|{target}"}
        if self.email:
            params["de"] = self.email
        try:
            resp = self.session.get(_ENDPOINT, params=params, timeout=_TIMEOUT)
            self._last_call = time.monotonic()
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            self.logger.warning("translate(%s→%s) failed: %s", source, target, exc)
            self._disabled = True  # stop hammering the API
            return None

        status = data.get("responseStatus")
        if status != 200:
            details = data.get("responseDetails") or ""
            self.logger.warning("MyMemory status %s (%s); disabling translator",
                                status, details)
            self._disabled = True
            return None

        translated = (data.get("responseData") or {}).get("translatedText")
        if not translated or translated.strip().upper() == text.upper():
            self._cache[key] = text  # no useful translation
            return text
        self._cache[key] = translated
        return translated

    def translate_menu(self, items: list[dict], source: str, target: str) -> list[dict]:
        """Translate title + description on each menu item. Returns new list."""
        out: list[dict] = []
        for it in items:
            new = dict(it)
            if it.get("title"):
                t = self.translate(it["title"], source, target)
                if t:
                    new["title"] = t
            if it.get("description"):
                d = self.translate(it["description"], source, target)
                if d:
                    new["description"] = d
            out.append(new)
        return out

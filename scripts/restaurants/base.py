"""Shared types and helpers for restaurant scrapers.

Each scraper module exports `fetch(today, session, logger) -> dict` with:

    {
        "id": "hortus",                 # stable slug
        "name": "Hortus",               # display name
        "url": "https://…",             # canonical restaurant URL
        "menus": {
            "de": {"items": [MenuItem, …]}  # or {"raw": "text block"}
            "en": {...},
            "fr": {...},
        },
        "pdf_url": "https://…" | None,  # optional link to full PDF
        "error": None | "message",      # non-fatal parsing warning
    }

A MenuItem is:

    {
        "title": "Spaghetti Carbonara",
        "description": "Speck, Schinken, …" | None,
        "price":  "CHF 18.50"           | None,
        "tags":   ["vegan", …]          | [],
    }

Scrapers should NEVER raise on network/parse failure — they should
return a stub entry with `error` populated so the page still renders.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; office-lunch-bot/1.0; "
        "+https://github.com/office-lunch)"
    ),
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8,fr;q=0.7",
}


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s


@dataclass
class Restaurant:
    id: str
    name: str
    url: str
    fetch: Callable
    languages: tuple[str, ...]


def empty_result(r: Restaurant, error: str, pdf_url: Optional[str] = None) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "url": r.url,
        "menus": {},
        "pdf_url": pdf_url,
        "error": error,
    }


def item(title: str, description: Optional[str] = None,
         price: Optional[str] = None, tags: Optional[list[str]] = None) -> dict:
    return {
        "title": title.strip(),
        "description": (description or "").strip() or None,
        "price": (price or "").strip() or None,
        "tags": tags or [],
    }

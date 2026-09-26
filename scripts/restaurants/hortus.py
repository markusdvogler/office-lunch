"""Hortus Kitchen — https://hortus.ch/en/kitchen/

Static HTML built by Astro. The weekly menu is a list of accordion items,
each with a weekday label, dish name, description, and allergens.
Same DOM shape in DE (/de/kitchen/) and EN (/en/kitchen/) — only the
weekday labels differ.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from .base import empty_result, item

ID = "hortus"
NAME = "Hortus Kitchen"
URL = "https://hortus.ch/en/kitchen/"
LANGUAGES = ("de", "en")

META = {
    "de": {"cuisine": "Vegetarisch, täglich frisch", "hours": "Mo–Fr 11:30–14:00"},
    "en": {"cuisine": "Vegetarian, made daily",     "hours": "Mo–Fri 11:30–14:00"},
    "fr": {"cuisine": "Végétarien, préparé chaque jour", "hours": "Lu–Ve 11:30–14:00"},
}

_URLS = {
    "de": "https://hortus.ch/de/kitchen/",
    "en": "https://hortus.ch/en/kitchen/",
}

_WEEKDAYS = {
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
}


def _parse(html, lang: str, today_weekday: int) -> Optional[dict]:
    """Return a MenuItem dict for today, or None if not found.

    `html` may be either a str or raw bytes; BeautifulSoup handles both.
    """
    soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")
    label = _WEEKDAYS[lang][today_weekday]

    for acc in soup.select("div.accordion-item"):
        weekday_el = acc.select_one("span.text-md")
        title_el = acc.select_one("span.text-h3")
        if not weekday_el or not title_el:
            continue
        if weekday_el.get_text(strip=True) != label:
            continue

        title = title_el.get_text(strip=True)
        tags = []
        # Hortus embeds "(vegan)" / "(vegetarian)" in the title itself.
        for marker in ("vegan", "vegetarisch", "vegetarian"):
            if f"({marker})" in title.lower():
                tags.append(marker if marker != "vegetarisch" else "vegetarian")

        desc_el = acc.select_one("div.panel p.text-lg")
        description = desc_el.get_text(" ", strip=True) if desc_el else None

        return item(title=title, description=description, tags=tags)

    return None


def fetch(today: date, session, logger) -> dict:
    weekday = today.weekday()  # Mon=0 … Sun=6
    restaurant_stub = type("R", (), {"id": ID, "name": NAME, "url": URL})()

    if weekday > 4:
        return {**empty_result(restaurant_stub, "closed on weekends"), "menus": {}}

    menus: dict[str, dict] = {}
    errors: list[str] = []

    for lang in LANGUAGES:
        try:
            resp = session.get(_URLS[lang], timeout=20)
            resp.raise_for_status()
            # Hortus doesn't send a charset — requests would guess
            # ISO-8859-1 and mangle umlauts. Pass raw bytes and let
            # BeautifulSoup read the <meta charset> tag.
            parsed = _parse(resp.content, lang, weekday)
            if parsed:
                menus[lang] = {"items": [parsed]}
            else:
                errors.append(f"{lang}: today's dish not found in HTML")
        except Exception as exc:
            errors.append(f"{lang}: {exc}")
            logger.warning("hortus %s: %s", lang, exc)

    return {
        "id": ID,
        "name": NAME,
        "url": URL,
        "meta": META,
        "menus": menus,
        "pdf_url": None,
        "error": "; ".join(errors) if errors and not menus else None,
    }

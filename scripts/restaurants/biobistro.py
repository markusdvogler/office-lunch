"""Bio Bistro — Bachgraben, https://biobistro.bsb.ch/standorte/bachgraben

Weekly menu is published as a PDF whose URL is linked from the page.
Each weekday block in the PDF looks roughly like:

    Freitag, 25. September   Salat oder Suppe   CHF 22.00
    Farfalle mit Pilzcrème,
    confierten Feigen & Parmesan-Chip

Followed by a long shared footer (Foodwaste note, phone/email,
meat/bread origin disclaimer) that we must strip.
"""
from __future__ import annotations

import io
import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import empty_result, item

ID = "biobistro"
NAME = "Bio Bistro (Bachgraben)"
URL = "https://biobistro.bsb.ch/standorte/bachgraben"
LANGUAGES = ("de",)

META = {
    "de": {"cuisine": "Bio-Küche mit Salatbuffet",     "hours": "Mo–Fr 11:00–14:00", "phone": "+41 61 326 70 10"},
    "en": {"cuisine": "Organic dishes & salad buffet", "hours": "Mo–Fri 11:00–14:00", "phone": "+41 61 326 70 10"},
    "fr": {"cuisine": "Bio, avec buffet de salades",   "hours": "Lu–Ve 11:00–14:00", "phone": "+41 61 326 70 10"},
}

_WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
_ALL_WEEKDAYS = _WEEKDAYS_DE + ["Samstag", "Sonntag"]

# Anything from here on is boilerplate, cut it.
_FOOTER_MARKERS = (
    "Um Foodwaste",
    "Reservationen",
    "+41 ",
    "bio-bistro-",
    "www.biobistro",
    "Unser Fleisch",
    "Alle unsere Brot",
    "Menuepreis",
    "Preise",
)

_PRICE_RE = re.compile(r"CHF\s*(\d{1,3}(?:[.,]\d{2})?)")


def _find_pdf(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[href$=".pdf"]'):
        href = a.get("href")
        if href and "Bio-Bistro" in href:
            return urljoin(URL, href)
    a = soup.select_one('a[href$=".pdf"]')
    return urljoin(URL, a["href"]) if a and a.get("href") else None


def _text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_today_block(text: str, today_weekday: int) -> Optional[str]:
    """Slice out today's block from the PDF text: everything from today's
    weekday marker up to the next weekday or the shared footer."""
    label = _WEEKDAYS_DE[today_weekday]
    idx = text.find(label)
    if idx < 0:
        return None
    tail = text[idx:]  # keep the weekday, we'll strip it later
    boundary = len(tail)

    # Cut at the next weekday (skip label at position 0 itself)
    for wd in _ALL_WEEKDAYS:
        j = tail.find(wd, len(label))
        if 0 < j < boundary:
            boundary = j

    # Cut at the first footer marker.
    for marker in _FOOTER_MARKERS:
        j = tail.find(marker)
        if 0 < j < boundary:
            boundary = j

    return tail[:boundary].strip(" :\n\t-,")


def _parse_block(block: str) -> Optional[dict]:
    """Turn today's block into a single MenuItem.

    First line is the header (weekday + date + category + price); the
    remaining lines are the dish name, potentially wrapped across lines.
    """
    lines = [ln.strip(" ,\t") for ln in block.splitlines() if ln.strip()]
    if not lines:
        return None

    header = lines[0]
    # Drop the "Weekday, DD. Month" prefix if present.
    for wd in _ALL_WEEKDAYS:
        header = re.sub(rf"^{wd},?\s*\d{{1,2}}\.?\s*[A-Za-zäöüÄÖÜ]*\s*", "", header)

    price = None
    m = _PRICE_RE.search(header)
    if m:
        price = f"CHF {m.group(1).replace(',', '.')}"
        header = _PRICE_RE.sub("", header)

    category = header.strip(" -·,")  # e.g. "Salat oder Suppe"
    dish_lines = lines[1:]

    # Join wrapped dish lines. Commas at end of a line = wrap.
    joined = " ".join(dish_lines).strip(" ,")
    if not joined:
        # Header itself contained the dish (some days have no wrap)
        if category and category.lower() not in ("salat oder suppe", "salat/suppe"):
            joined = category
            category = ""

    if not joined:
        return None

    tags = []
    joined_lc = joined.lower()
    if "vegan" in joined_lc:
        tags.append("vegan")
    elif "vegi" in joined_lc or "vegetarisch" in joined_lc:
        tags.append("vegetarian")

    description = f"inkl. {category}" if category else None
    return item(title=joined, description=description, price=price, tags=tags)


def fetch(today: date, session, logger) -> dict:
    stub = type("R", (), {"id": ID, "name": NAME, "url": URL})()
    weekday = today.weekday()
    if weekday > 4:
        return empty_result(stub, "closed on weekends")

    try:
        resp = session.get(URL, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        return empty_result(stub, f"page fetch failed: {exc}")

    pdf_url = _find_pdf(resp.text)
    if not pdf_url:
        return empty_result(stub, "no PDF link found on page")

    menus: dict = {}
    try:
        pdf_resp = session.get(pdf_url, timeout=30)
        pdf_resp.raise_for_status()
        text = _text_from_pdf(pdf_resp.content)
        block = _extract_today_block(text, weekday) if text else None
        parsed = _parse_block(block) if block else None
        if parsed:
            menus["de"] = {"items": [parsed]}
    except Exception as exc:
        logger.warning("biobistro pdf: %s", exc)

    return {
        "id": ID,
        "name": NAME,
        "url": URL,
        "meta": META,
        "menus": menus,
        "pdf_url": pdf_url,
        "error": None,
    }

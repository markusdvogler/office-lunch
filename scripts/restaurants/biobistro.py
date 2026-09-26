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


_HEADER_PREFIX = re.compile(
    r"^\s*(?:" + "|".join(_ALL_WEEKDAYS) + r"),?\s*\d{1,2}\.?\s*[A-Za-zäöüÄÖÜ]*\s*"
)
_SALAT_SUPPE = re.compile(r"\s*Salat\s*(?:oder|/)\s*Suppe\s*", re.IGNORECASE)
_FLEISCH_HEADER = re.compile(r"^\s*Fleisch[-\s]*Men[uü]\s*$", re.IGNORECASE)


def _extract_today_block(text: str, today_weekday: int) -> Optional[str]:
    """Slice out today's block: from today's weekday marker up to the
    next weekday or the shared footer."""
    label = _WEEKDAYS_DE[today_weekday]
    idx = text.find(label)
    if idx < 0:
        return None
    tail = text[idx:]
    boundary = len(tail)
    for wd in _ALL_WEEKDAYS:
        j = tail.find(wd, len(label))
        if 0 < j < boundary:
            boundary = j
    for marker in _FOOTER_MARKERS:
        j = tail.find(marker)
        if 0 < j < boundary:
            boundary = j
    return tail[:boundary]


def _parse_block(block: str) -> list[dict]:
    """Turn today's block into a list of MenuItem dicts.

    The PDF lays out weekday + date on the left, dish name (wrapped)
    in the middle, and prices in a right-aligned column — so after
    text extraction we see prices interleaved. We collect all prices
    once, strip them out, then read what's left as the dish name.
    Some days have both a Vegi option and a "Fleisch-Menu" separator
    followed by a meat variant — those become two items.
    """
    prices = [f"CHF {p.replace(',', '.')}"
              for p in _PRICE_RE.findall(block)]

    lines: list[str] = []
    for raw in block.splitlines():
        ln = raw
        ln = _HEADER_PREFIX.sub("", ln, count=1)
        ln = _SALAT_SUPPE.sub(" ", ln)
        ln = _PRICE_RE.sub("", ln)
        ln = ln.strip(" ,\t")
        if not ln:
            continue
        # Skip filler lines like ", ." or ".", left after price stripping.
        if not re.search(r"[A-Za-zäöüÄÖÜßé]", ln):
            continue
        lines.append(ln)

    if not lines:
        return []

    # Split into groups by "Fleisch-Menu" marker.
    groups: list[list[str]] = [[]]
    tag_per_group: list[Optional[str]] = [None]
    for ln in lines:
        if _FLEISCH_HEADER.match(ln):
            groups.append([])
            tag_per_group.append("meat")
            continue
        groups[-1].append(ln)

    items: list[dict] = []
    used_prices = 0
    for i, group in enumerate(groups):
        if not group:
            continue
        title = " ".join(group).strip(" ,")
        title = re.sub(r"\s+", " ", title).replace(" ,", ",")
        if not title:
            continue
        # Attach the next unused price to this group.
        price = prices[used_prices] if used_prices < len(prices) else None
        used_prices += 1
        tags = []
        lc = title.lower()
        if "vegan" in lc:
            tags.append("vegan")
        elif "vegi" in lc or "vegetarisch" in lc:
            tags.append("vegetarian")
        elif tag_per_group[i] is None and len(groups) > 1:
            # Days with a Vegi + Fleisch split — the first group is Vegi.
            tags.append("vegetarian")
        items.append(item(
            title=title,
            description="inkl. Salat oder Suppe",
            price=price,
            tags=tags,
        ))
    return items


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
        items = _parse_block(block) if block else []
        if items:
            menus["de"] = {"items": items}
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

"""Bio Bistro — Bachgraben, https://biobistro.bsb.ch/standorte/bachgraben

Weekly menu is published as a PDF whose URL is linked from the page:
    …/Bio-Bistro/{YY}KW-{WW}.pdf   (YY = 2-digit year, WW = ISO week)

Strategy: fetch the page HTML, grab the first .pdf link (their template
always points to the current week), download and text-extract it, then
try to slice out today's block by German weekday markers. If that fails
we still return the PDF URL so the frontend can link to it.
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

_WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]


def _find_pdf(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[href$=".pdf"]'):
        href = a.get("href")
        if href and "Bio-Bistro" in href:
            return urljoin(URL, href)
    # Fallback: any first PDF link on the page.
    a = soup.select_one('a[href$=".pdf"]')
    return urljoin(URL, a["href"]) if a and a.get("href") else None


def _extract_today(text: str, today_weekday: int) -> Optional[str]:
    """Return the raw text block for today's weekday from a menu PDF."""
    if today_weekday > 4:
        return None
    label = _WEEKDAYS_DE[today_weekday]
    # Find today's marker, cut until the next weekday or end-of-doc.
    idx = text.lower().find(label.lower())
    if idx < 0:
        return None
    tail = text[idx + len(label):]
    boundary = len(tail)
    for wd in _WEEKDAYS_DE + ["Samstag", "Sonntag", "Preise", "Menuepreis"]:
        j = tail.lower().find(wd.lower())
        if 3 < j < boundary:  # skip zero-width match
            boundary = j
    block = tail[:boundary].strip(" :\n\t-")
    # Collapse excessive whitespace but keep line breaks.
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    return "\n".join(lines) if lines else None


def _text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


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
        block = _extract_today(text, weekday) if text else None
        if block:
            # Try to split lines into individual dishes: many bistro PDFs
            # use two columns for menu options, joined into single lines.
            lines = [ln for ln in block.split("\n") if ln.strip()]
            if len(lines) <= 6:
                items = [item(title=ln) for ln in lines]
                menus["de"] = {"items": items}
            else:
                menus["de"] = {"raw": block}
    except Exception as exc:
        logger.warning("biobistro pdf: %s", exc)

    result = {
        "id": ID,
        "name": NAME,
        "url": URL,
        "menus": menus,
        "pdf_url": pdf_url,
        "error": None if menus else "PDF menu available — daily text could not be extracted",
    }
    return result

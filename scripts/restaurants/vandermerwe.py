"""Van der Merwe — https://vandermerwe.ch/gastronomie/

Publishes a static menu PDF; no daily rotation is exposed on the site.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import empty_result

ID = "vandermerwe"
NAME = "Van der Merwe"
URL = "https://vandermerwe.ch/gastronomie/"
LANGUAGES = ("de",)

META = {
    "de": {"cuisine": "Hausmannskost & Fitness Food",   "hours": "Mo–Fr 11:00–14:00", "phone": "+41 61 487 98 98"},
    "en": {"cuisine": "Swiss homestyle & fitness food",  "hours": "Mo–Fri 11:00–14:00", "phone": "+41 61 487 98 98"},
    "fr": {"cuisine": "Cuisine suisse & fitness food",   "hours": "Lu–Ve 11:00–14:00", "phone": "+41 61 487 98 98"},
}


def _find_pdf(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[href$=".pdf"]'):
        href = a.get("href", "")
        if "Speisekarte" in href or "VDM" in href:
            return urljoin(URL, href)
    a = soup.select_one('a[href$=".pdf"]')
    return urljoin(URL, a["href"]) if a and a.get("href") else None


def fetch(today: date, session, logger) -> dict:
    stub = type("R", (), {"id": ID, "name": NAME, "url": URL})()
    if today.weekday() > 4:
        return empty_result(stub, "closed on weekends")
    try:
        resp = session.get(URL, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        return empty_result(stub, f"page fetch failed: {exc}")
    pdf_url = _find_pdf(resp.text)
    return {
        "id": ID,
        "name": NAME,
        "url": URL,
        "meta": META,
        "menus": {},
        "pdf_url": pdf_url,
        "pdf_only": True,
        "error": None,
    }

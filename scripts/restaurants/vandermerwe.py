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
        "menus": {},
        "pdf_url": pdf_url,
        "error": "Restaurant publishes a static menu (no daily rotation online)",
    }

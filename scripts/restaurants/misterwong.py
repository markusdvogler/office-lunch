"""Mister Wong — https://www.misterwong.ch/standorte/allschwil/

They advertise a rotating "Daily-Wok" but the website only publishes
the general restaurant menu as a single PDF. Best we can do is surface
the PDF link and a fixed note; the frontend renders that gracefully.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import empty_result

ID = "misterwong"
NAME = "Mister Wong (Allschwil)"
URL = "https://www.misterwong.ch/standorte/allschwil/"
LANGUAGES = ("de",)


def _find_pdf(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[href$=".pdf"]'):
        href = a.get("href", "")
        if "Speisekarte" in href or "Menue" in href or "menu" in href.lower():
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
        "error": "Daily-Wok changes daily; full menu published as PDF only",
    }

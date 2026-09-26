"""Van der Merwe — https://vandermerwe.ch/gastronomie/

Standing menu, no daily rotation online. We surface the lunch-friendly
highlights (Fitness Food, Burger, kleines Menü) so users can decide
without opening a PDF. The Tagessuppe changes daily but isn't published.

Highlights copied from Speisekarte_VDM.pdf (Dec 2023). Update manually
if it changes.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import empty_result, item

ID = "vandermerwe"
NAME = "Van der Merwe"
URL = "https://vandermerwe.ch/gastronomie/"
LANGUAGES = ("de",)

META = {
    "de": {"cuisine": "Hausmannskost & Fitness Food",  "hours": "Mo–Fr 11:00–14:00", "phone": "+41 61 487 98 98"},
    "en": {"cuisine": "Swiss homestyle & fitness food", "hours": "Mo–Fri 11:00–14:00", "phone": "+41 61 487 98 98"},
    "fr": {"cuisine": "Cuisine suisse & fitness food",  "hours": "Lu–Ve 11:00–14:00", "phone": "+41 61 487 98 98"},
}

_HIGHLIGHTS_DE = [
    {"title": "Fitnessteller mit Poulet",
     "description": "Pouletbrust vom Grill mit buntem Beilagen-Salat",
     "price": "Fr. 16.50", "tags": []},
    {"title": "Fitnessteller mit Lachs",
     "description": "Lachsfilet gebraten mit buntem Beilagen-Salat",
     "price": "Fr. 18.00", "tags": []},
    {"title": "Classic Burger",
     "description": "Rindsburger mit Tomate, Gurke, Zwiebeln und Salat oder Pommes",
     "price": "Fr. 18.00", "tags": []},
    {"title": "Vegi-Burger",
     "description": "mit Gurke, Zwiebeln, Tomate und Salat oder Pommes",
     "price": "Fr. 20.00", "tags": ["vegetarian"]},
    {"title": "Hausgemachte Quiche",
     "description": "mit gemischtem Salat",
     "price": "Fr. 14.50", "tags": ["vegetarian"]},
    {"title": "Poulet-Schnitzelbrot Provençale",
     "description": "mit gemischtem Salat oder Pommes",
     "price": "Fr. 13.50", "tags": []},
    {"title": "Tagessuppe",
     "description": "wechselnd nach Angebot",
     "price": "Fr. 6.00", "tags": []},
]


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
        pdf_url = _find_pdf(resp.text)
    except Exception as exc:
        logger.warning("vandermerwe page fetch: %s", exc)
        pdf_url = None

    return {
        "id": ID,
        "name": NAME,
        "url": URL,
        "meta": META,
        "menus": {"de": {"items": _HIGHLIGHTS_DE, "note": "standing-menu"}},
        "pdf_url": pdf_url,
        "error": None,
    }

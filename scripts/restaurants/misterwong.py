"""Mister Wong — https://www.misterwong.ch/standorte/allschwil/

They serve a standing menu (no daily rotation). Rather than dumping the
user on a PDF, we surface the popular lunch dishes with their portion
prices so people can decide at a glance. The PDF link stays as a
'full menu' fallback for the long tail.

Highlights are copied from the published Speisekarte
(VAL_RZ_2_Mister_Wong_Speisekarte_A1_LOW.pdf, Sep 2025). If the menu
changes we'd update this list manually.
"""
from __future__ import annotations

from datetime import date
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import empty_result, item

ID = "misterwong"
NAME = "Mister Wong (Allschwil)"
URL = "https://www.misterwong.ch/standorte/allschwil/"
LANGUAGES = ("de",)

META = {
    "de": {"cuisine": "Asiatische Wok-Küche & Curries", "hours": "Mo–Fr 11:00–14:00, 17:00–22:00"},
    "en": {"cuisine": "Asian wok dishes & curries",     "hours": "Mo–Fri 11:00–14:00, 17:00–22:00"},
    "fr": {"cuisine": "Cuisine asiatique wok & curries", "hours": "Lu–Ve 11:00–14:00, 17:00–22:00"},
}

# The dishes people actually order at lunch. Not the full 30-item card.
_HIGHLIGHTS_DE = [
    {"title": "Chicken Fried Rice",
     "description": "Gebratener Reis, Poulet, Ei, frisches Gemüse, Sojasauce",
     "price": "CHF 15.00", "tags": []},
    {"title": "Vegetable Fried Rice",
     "description": "Gebratener Reis, Ei, schwarze Pilze, frisches Gemüse",
     "price": "CHF 14.00", "tags": ["vegetarian"]},
    {"title": "Chicken Fried Noodles",
     "description": "Gebratene Nudeln, Poulet, Ei, Gemüse, Sojasauce",
     "price": "CHF 17.00", "tags": []},
    {"title": "Phad Thai (Poulet)",
     "description": "Reisnudeln, Ei, Frühlingszwiebeln, Cashewnüsse, Sojasprossen, Limetten",
     "price": "CHF 21.50", "tags": []},
    {"title": "Yellow Curry (Poulet)",
     "description": "Mildes Curry mit Peperoni, Ananas, Kartoffeln, Tomaten, Reis",
     "price": "CHF 21.50", "tags": []},
    {"title": "Green Curry (Tofu)",
     "description": "Scharfes Curry mit Peperoni, Ananas, Kartoffeln, Tomaten, Reis",
     "price": "CHF 21.50", "tags": ["vegetarian"]},
]


def _find_pdf(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select('a[href$=".pdf"]'):
        href = a.get("href", "")
        if "Speisekarte" in href or "menu" in href.lower():
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
        logger.warning("misterwong page fetch: %s", exc)
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

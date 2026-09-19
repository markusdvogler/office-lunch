"""Belo Café Swiss TPH — Food2050-hosted (own organization, not under zfv)."""
from datetime import date

from .food2050 import fetch_food2050

ID = "belo-cafe"
NAME = "Belo Café Swiss TPH"
URL = "https://www.zfv.ch/de/essen-gehen/belo-cafe-swiss-tph"

IFRAME_URLS = {
    "de": "https://app.food2050.ch/de/belo/belo/menu/mittagsmenue/weekly",
    "fr": "https://app.food2050.ch/fr/belo/belo/menu/mittagsmenue/weekly",
}


def fetch(today: date, session, logger) -> dict:
    return fetch_food2050(
        id=ID, name=NAME, url=URL, iframe_urls=IFRAME_URLS,
        today=today, session=session, logger=logger,
    )

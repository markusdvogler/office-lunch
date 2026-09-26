"""Belo Café Swiss TPH — Food2050-hosted (own organization, not under zfv)."""
from datetime import date

from .food2050 import fetch_food2050

ID = "belo-cafe"
NAME = "Belo Café Swiss TPH"
URL = "https://www.zfv.ch/de/essen-gehen/belo-cafe-swiss-tph"

META = {
    "de": {"cuisine": "Kantine: Veggie, Traditional, Soul Food", "hours": "Mo–Fr, Mittagsverpflegung"},
    "en": {"cuisine": "Canteen: veggie, traditional, soul food",   "hours": "Mo–Fri, lunch service"},
    "fr": {"cuisine": "Cantine : végétarien, traditionnel, soul food", "hours": "Lu–Ve, service de midi"},
}

IFRAME_URLS = {
    "de": "https://app.food2050.ch/de/belo/belo/menu/mittagsmenue/weekly",
    "fr": "https://app.food2050.ch/fr/belo/belo/menu/mittagsmenue/weekly",
}


def fetch(today: date, session, logger) -> dict:
    result = fetch_food2050(
        id=ID, name=NAME, url=URL, iframe_urls=IFRAME_URLS,
        today=today, session=session, logger=logger,
    )
    result["meta"] = META
    return result

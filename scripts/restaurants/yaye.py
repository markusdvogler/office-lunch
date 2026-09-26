"""YAYE (ZFV Main Campus) — Food2050-hosted menu."""
from datetime import date

from .food2050 import fetch_food2050

ID = "yaye"
NAME = "YAYE"
URL = "https://www.zfv.ch/de/essen-gehen/yaye"

META = {
    "de": {"cuisine": "Kantine: Glocal, Traditional, Salate", "hours": "Mo–Fr 08:30–14:30 · Warme Küche 11:30–13:30"},
    "en": {"cuisine": "Canteen: global, traditional & salads",  "hours": "Mo–Fri 08:30–14:30 · Hot dishes 11:30–13:30"},
    "fr": {"cuisine": "Cantine : cuisine internationale & salades", "hours": "Lu–Ve 08:30–14:30 · Chaud 11:30–13:30"},
}

IFRAME_URLS = {
    "de": "https://app.food2050.ch/de/v2/zfv/main-campus/yaye/mittagsverpflegung/menu/weekly",
    "fr": "https://app.food2050.ch/fr/v2/zfv/main-campus/yaye/mittagsverpflegung/menu/weekly",
}


def fetch(today: date, session, logger) -> dict:
    result = fetch_food2050(
        id=ID, name=NAME, url=URL, iframe_urls=IFRAME_URLS,
        today=today, session=session, logger=logger,
    )
    result["meta"] = META
    return result

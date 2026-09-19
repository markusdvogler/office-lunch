"""YAYE (ZFV Main Campus) — Food2050-hosted menu."""
from datetime import date

from .food2050 import fetch_food2050

ID = "yaye"
NAME = "YAYE"
URL = "https://www.zfv.ch/de/essen-gehen/yaye"

IFRAME_URLS = {
    "de": "https://app.food2050.ch/de/v2/zfv/main-campus/yaye/mittagsverpflegung/menu/weekly",
    "fr": "https://app.food2050.ch/fr/v2/zfv/main-campus/yaye/mittagsverpflegung/menu/weekly",
}


def fetch(today: date, session, logger) -> dict:
    return fetch_food2050(
        id=ID, name=NAME, url=URL, iframe_urls=IFRAME_URLS,
        today=today, session=session, logger=logger,
    )

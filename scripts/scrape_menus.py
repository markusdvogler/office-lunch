"""Scrape today's lunch menu from each configured restaurant and
write the aggregate JSON to ../data/menus.json.

Run: python scripts/scrape_menus.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# Local imports (this file lives in scripts/)
sys.path.insert(0, str(Path(__file__).parent))

from restaurants import (  # noqa: E402
    base,
    hortus,
    biobistro,
    yaye,
    belo_cafe,
    misterwong,
    vandermerwe,
)
from translator import Translator  # noqa: E402

RESTAURANTS = [hortus, biobistro, yaye, belo_cafe, misterwong, vandermerwe]

TARGET_LANGUAGES = ("de", "en", "fr")
# Preferred source order when filling a missing target language: DE first
# because five of six restaurants publish DE natively.
FALLBACK_ORDER = ("de", "en", "fr")

WEEKDAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


def _fill_missing_languages(restaurants: list[dict], translator: Translator,
                            logger: logging.Logger) -> None:
    """For each restaurant, translate items into any missing target language.

    Only restaurants that scraped at least one language with `items` are
    translated — PDF-only entries have no text to translate."""
    for r in restaurants:
        menus = r.get("menus") or {}
        # Pick source language (first available with items, in preferred order).
        source = None
        for lang in FALLBACK_ORDER:
            if lang in menus and menus[lang].get("items"):
                source = lang
                break
        if source is None:
            continue
        source_items = menus[source]["items"]
        for target in TARGET_LANGUAGES:
            if target == source or target in menus:
                continue
            logger.info("  translating %s: %s → %s", r["id"], source, target)
            translated = translator.translate_menu(source_items, source, target)
            menus[target] = {
                "items": translated,
                "translated_from": source,
            }
        r["menus"] = menus


def scrape(today: date, translate: bool = True) -> dict:
    logger = logging.getLogger("scrape")
    session = base.make_session()
    results = []
    for mod in RESTAURANTS:
        logger.info("Scraping %s", mod.NAME)
        try:
            entry = mod.fetch(today, session, logger)
        except Exception as exc:
            logger.exception("Fatal error scraping %s", mod.NAME)
            entry = {
                "id": mod.ID, "name": mod.NAME, "url": mod.URL,
                "menus": {}, "pdf_url": None,
                "error": f"scraper crashed: {exc}",
            }
        # Ensure required shape
        entry.setdefault("menus", {})
        entry.setdefault("pdf_url", None)
        entry.setdefault("error", None)
        results.append(entry)

    if translate:
        translator = Translator(session=session, logger=logger)
        _fill_missing_languages(results, translator, logger)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "date": today.isoformat(),
        "weekday": WEEKDAY_NAMES[today.weekday()],
        "restaurants": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Override 'today' (YYYY-MM-DD) for testing")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON to stdout, don't write file")
    parser.add_argument("--out", default=None, help="Path to output JSON (default: ../data/menus.json)")
    parser.add_argument("--no-translate", action="store_true",
                        help="Skip auto-translation of missing languages")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    today = date.fromisoformat(args.date) if args.date else date.today()
    data = scrape(today, translate=not args.no_translate)
    payload = json.dumps(data, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(payload)
        return

    out_path = Path(args.out) if args.out else Path(__file__).parent.parent / "data" / "menus.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

"""Helper for zfv.ch restaurants that embed the Food2050 iframe.

Food2050 is a Next.js app. Its initial HTML embeds the GraphQL query
result for the weekly menu — dishes are nested inside
`week.daily[].menuItems[].dish`, keyed by `dateLocal`.

We extract dishes with a regex against the (unescaped) payload; parsing
the RSC stream properly would be more brittle than this.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from .base import empty_result, item


def _unescape(js_string: str) -> str:
    return (
        js_string
        .replace("\\u002F", "/")
        .replace('\\"', '"')
        .replace("\\n", " ")
        .replace("\\/", "/")
    )


# One menuItem block: category name + dish name + description + veg flags.
_ITEM_RE = re.compile(
    r'"category":\{[^}]*?"name":"(?P<category>[^"]{1,60})"\}'
    r'.*?"isVegan":(?P<vegan>true|false)'
    r'.*?"isVegetarian":(?P<veg>true|false)'
    r'.*?"name":"(?P<name>[^"]{1,120})"'
    r',"description":"(?P<desc>[^"]{0,400})"',
    re.DOTALL,
)

# Locate a day block by its dateLocal, then extract everything up to the
# next day marker (or the end).
_DAY_MARKER = re.compile(
    r'"dateLocal":"(?P<date>\d{4}-\d{2}-\d{2})T[^"]*"\}(?P<body>.*?)'
    r'(?=(?:"dateLocal":"\d{4}-\d{2}-\d{2}T)|$)',
    re.DOTALL,
)


def _parse_day(payload: str, target: date) -> list[dict]:
    target_iso = target.isoformat()
    items: list[dict] = []
    seen_titles: set[str] = set()
    for match in _DAY_MARKER.finditer(payload):
        if match.group("date") != target_iso:
            continue
        body = match.group("body")
        # Stop at the boundary of the surrounding daily[] array to avoid
        # bleeding into unrelated data.
        body = body.split('"info":[', 1)[0]
        for m in _ITEM_RE.finditer(body):
            title = m.group("name").strip()
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            tags = []
            if m.group("vegan") == "true":
                tags.append("vegan")
            elif m.group("veg") == "true":
                tags.append("vegetarian")
            category = m.group("category").strip()
            desc = m.group("desc").strip()
            # Prepend category to description for context.
            description = f"{category} · {desc}" if desc else category
            items.append(item(title=title, description=description, tags=tags))
    return items


def fetch_food2050(*, id: str, name: str, url: str,
                   iframe_urls: dict[str, str],
                   today: date, session, logger) -> dict:
    """Scrape a Food2050-hosted menu for each (lang, iframe_url) pair."""
    stub = type("R", (), {"id": id, "name": name, "url": url})()
    if today.weekday() > 4:
        return empty_result(stub, "closed on weekends")

    menus: dict[str, dict] = {}
    errors: list[str] = []

    for lang, iframe_url in iframe_urls.items():
        try:
            resp = session.get(iframe_url, timeout=30)
            resp.raise_for_status()
            payload = _unescape(resp.text)
            items = _parse_day(payload, today)
            if items:
                menus[lang] = {"items": items}
            else:
                errors.append(f"{lang}: no menu items found for {today.isoformat()}")
        except Exception as exc:
            errors.append(f"{lang}: {exc}")
            logger.warning("%s %s: %s", id, lang, exc)

    return {
        "id": id,
        "name": name,
        "url": url,
        "menus": menus,
        "pdf_url": None,
        "error": "; ".join(errors) if errors and not menus else None,
    }

"""Helper for zfv.ch restaurants that embed the Food2050 iframe.

Food2050 is a Next.js app. Its initial HTML embeds the GraphQL query
result as a React Server Components payload; dishes are nested inside
`week.daily[].menuItems[].dish`, keyed by `dateLocal`.

We extract dishes with a regex against the (unescaped) payload; parsing
the RSC stream properly would be more brittle than this.

Category names can be either inlined (`"category":{...,"name":"..."}`)
or, thanks to RSC deduplication, references (`"category":"$7:..."`).
The safer signal is the `detailUrl` — its second-to-last path segment
is a comma-separated list like `mittagsverpflegung,hauptspeisen,glocal`
and the last piece is the category slug. We convert that back to a
display label.
"""
from __future__ import annotations

import re
from datetime import date

from .base import empty_result, item


_UNICODE_ESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def _unescape(js_string: str) -> str:
    # Order matters: first collapse \\uXXXX escapes to real chars, then
    # normalise the JS-string escapes.
    js_string = _UNICODE_ESC.sub(
        lambda m: chr(int(m.group(1), 16)), js_string
    )
    return (
        js_string
        .replace('\\"', '"')
        .replace("\\n", " ")
        .replace("\\/", "/")
    )


# Anchor on the menuItem's dish object — every menuItem contains one
# even when its category is a reference. We look inside the dish for
# the veg flags, name, description in order.
_ITEM_RE = re.compile(
    r'"__typename":"OutletMenuItemDish"'
    r'(?:(?!"__typename":"OutletMenuItemDish").)*?'
    r'"detailUrl":"(?P<detail>[^"]+)"'
    r'(?:(?!"__typename":"OutletMenuItemDish").)*?'
    r'"isVegan":(?P<vegan>true|false),'
    r'"isVegetarian":(?P<veg>true|false),'
    r'(?:(?!"__typename":"OutletMenuItemDish").)*?'
    r'"name":"(?P<name>[^"]{1,150})"'
    r',"description":"(?P<desc>[^"]{0,500})"',
    re.DOTALL,
)

# Locate a day block by its dateLocal, then extract everything up to the
# next day marker (or the end).
_DAY_MARKER = re.compile(
    r'"dateLocal":"(?P<date>\d{4}-\d{2}-\d{2})T[^"]*"\}(?P<body>.*?)'
    r'(?=(?:"dateLocal":"\d{4}-\d{2}-\d{2}T)|$)',
    re.DOTALL,
)


def _category_from_detail(detail_url: str) -> str:
    """
    Extract a display category from a detailUrl like
    `.../mittagsverpflegung,hauptspeisen,glocal/2026-09-25`.

    Returns 'Glocal' or 'Weekly Special' or '' if unrecognised.
    """
    parts = detail_url.rstrip("/").split("/")
    if len(parts) < 2:
        return ""
    segment = parts[-2]  # e.g. "mittagsverpflegung,hauptspeisen,glocal"
    # Prefer the last comma-separated piece (specific category).
    slug = segment.split(",")[-1]
    if slug in ("mittagsverpflegung", "mittagsmenue", "hauptspeisen", "menu"):
        return ""
    return slug.replace("-", " ").title()


def _parse_day(payload: str, target: date) -> list[dict]:
    target_iso = target.isoformat()
    items: list[dict] = []
    seen_titles: set[str] = set()
    for match in _DAY_MARKER.finditer(payload):
        if match.group("date") != target_iso:
            continue
        body = match.group("body")
        # Trim to just this day's menuItems array (avoid bleeding into
        # sibling days that share their category reference).
        body = body.split('"info":[', 1)[0]
        for m in _ITEM_RE.finditer(body):
            title = m.group("name").strip()
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            tags = []
            if m.group("vegan") == "true":
                tags.append("vegan")
            elif m.group("veg") == "true":
                tags.append("vegetarian")
            desc = m.group("desc").strip()
            category = _category_from_detail(m.group("detail"))
            description = f"{category} · {desc}" if category and desc else (desc or category or None)
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
            resp.encoding = resp.encoding or "utf-8"
            payload = _unescape(resp.text)
            items_out = _parse_day(payload, today)
            if items_out:
                menus[lang] = {"items": items_out}
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

"""Marktplaats.nl scraper - fetches listings from search URLs."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
}

PRICE_TYPE_MAP = {
    "SEE_DESCRIPTION": "Zie omschrijving",
    "NOTK": "n.o.t.k.",
    "FREE": "Gratis",
    "FAST_BID": "Bieden",
    "ON_DEMAND": "Op aanvraag",
}


@dataclass
class Listing:
    mp_id: str
    title: str
    price: str
    url: str
    image_url: Optional[str]
    description: Optional[str]


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_listings(search_url: str, session: requests.Session) -> list[Listing]:
    """Fetch listings from a Marktplaats search URL."""
    try:
        resp = session.get(search_url, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        listings = _parse_page(resp.text)
        logger.debug(f"Fetched {len(listings)} listings from {search_url}")
        return listings
    except requests.RequestException as e:
        logger.error(f"Error fetching {search_url}: {e}")
        return []


def _parse_page(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")

    # Strategy 1: __NEXT_DATA__ (Next.js SSR)
    next_script = soup.find("script", id="__NEXT_DATA__")
    if next_script and next_script.string:
        listings = _parse_next_data(next_script.string)
        if listings:
            return listings

    # Strategy 2: Search for JSON blobs containing listings arrays
    for script in soup.find_all("script"):
        src = script.string or ""
        if '"listings"' in src and '"itemId"' in src:
            try:
                # Find the outermost JSON object
                match = re.search(r"(\{.+\})", src, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    listings = _extract_from_any_json(data)
                    if listings:
                        return listings
            except (json.JSONDecodeError, ValueError):
                pass

    # Strategy 3: HTML fallback
    return _parse_html(soup)


def _parse_next_data(json_str: str) -> list[Listing]:
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return []

    # Try known paths first
    page_props = data.get("props", {}).get("pageProps", {})
    candidates = [
        page_props.get("listings"),
        page_props.get("searchRequestAndResponse", {}).get("listings"),
        page_props.get("data", {}).get("listings"),
        _deep_find(page_props, "listings"),
        _deep_find(data, "listings"),
    ]

    for candidate in candidates:
        if candidate and isinstance(candidate, list):
            result = _parse_listing_items(candidate)
            if result:
                return result

    return []


def _extract_from_any_json(data: dict) -> list[Listing]:
    listings_data = data.get("listings")
    if isinstance(listings_data, list) and listings_data:
        return _parse_listing_items(listings_data)
    found = _deep_find(data, "listings")
    if found:
        return _parse_listing_items(found)
    return []


def _deep_find(obj, key: str, depth: int = 0):
    """Recursively search nested dicts/lists for a key whose value is a non-empty list."""
    if depth > 8:
        return None
    if isinstance(obj, dict):
        val = obj.get(key)
        if isinstance(val, list) and val:
            return val
        for v in obj.values():
            result = _deep_find(v, key, depth + 1)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj[:3]:
            result = _deep_find(item, key, depth + 1)
            if result is not None:
                return result
    return None


def _parse_listing_items(items: list) -> list[Listing]:
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue

        mp_id = str(
            item.get("itemId")
            or item.get("id")
            or item.get("advertisementId")
            or ""
        )
        title = item.get("title", "").strip()
        if not title:
            continue

        # Price
        price_info = item.get("priceInfo") or {}
        if price_info:
            cents = price_info.get("priceCents")
            if cents is not None:
                price = f"€{cents / 100:.2f}"
            else:
                price_type = price_info.get("priceType", "")
                price = PRICE_TYPE_MAP.get(price_type, price_type or "Prijs onbekend")
        else:
            raw = item.get("price") or item.get("displayPrice") or ""
            price = str(raw) if raw else "Prijs onbekend"

        # URL
        vip_url = item.get("vipUrl") or item.get("url") or ""
        url = f"https://www.marktplaats.nl{vip_url}" if vip_url.startswith("/") else vip_url

        # Image
        image_url = None
        pictures = item.get("pictures") or item.get("images") or []
        if pictures:
            pic = pictures[0]
            if isinstance(pic, dict):
                image_url = (
                    pic.get("mediumUrl")
                    or pic.get("url")
                    or pic.get("extraSmallUrl")
                    or ""
                )
            elif isinstance(pic, str):
                image_url = pic

        description = (item.get("description") or "")[:300].strip()

        results.append(
            Listing(
                mp_id=mp_id or title[:20],
                title=title,
                price=price,
                url=url,
                image_url=image_url or None,
                description=description or None,
            )
        )

    return results


def _parse_html(soup: BeautifulSoup) -> list[Listing]:
    """Last-resort HTML parser."""
    results = []

    articles = (
        soup.find_all(attrs={"data-item-id": True})
        or soup.find_all(attrs={"data-listing-id": True})
        or soup.find_all("article", class_=re.compile(r"Listing|listing|mp-Listing"))
        or soup.find_all("li", class_=re.compile(r"Listing|listing|mp-Listing"))
    )

    for art in articles:
        mp_id = (
            art.get("data-item-id")
            or art.get("data-listing-id")
            or art.get("id", "").replace("listing-", "")
        )

        title_el = art.find(["h2", "h3"]) or art.find(
            class_=re.compile(r"[Tt]itle")
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        link = art.find("a", href=re.compile(r"/a/|/m/|marktplaats"))
        url = link["href"] if link else ""
        if url.startswith("/"):
            url = f"https://www.marktplaats.nl{url}"

        price_el = art.find(class_=re.compile(r"[Pp]rice"))
        price = price_el.get_text(strip=True) if price_el else "Prijs onbekend"

        img = art.find("img")
        image_url = img.get("src") or img.get("data-src") if img else None

        results.append(
            Listing(
                mp_id=mp_id or url.split("/")[-1],
                title=title,
                price=price,
                url=url,
                image_url=image_url,
                description=None,
            )
        )

    return results

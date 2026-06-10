import re
import logging
import requests
from urllib.parse import urlparse, parse_qs, unquote

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
    'Accept-Language': 'nl-NL,nl;q=0.9',
    'Referer': 'https://www.marktplaats.nl/',
}

API_URL = 'https://www.marktplaats.nl/lrp/api/search'


def parse_search_url(url: str) -> dict:
    """Convert a browser Marktplaats URL into API query parameters."""
    parsed = urlparse(url)

    # Query string params (e.g. ?query=...&priceFrom=...)
    qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    # Hash/fragment params — Marktplaats puts filters there in newer URLs
    frag = {}
    if parsed.fragment:
        frag = {k: v[0] for k, v in parse_qs(parsed.fragment).items()}

    params = {**frag, **qs}  # query string wins on conflict

    # Drop UI-only keys
    for key in ('Language', 'sellingFastOnly', 'searchInTitleAndDescription'):
        params.pop(key, None)

    path_parts = [p for p in parsed.path.split('/') if p]

    # /q/<term>/ style URL
    if path_parts and path_parts[0] == 'q' and len(path_parts) > 1:
        params.setdefault('query', unquote(path_parts[1]).replace('-', ' '))

    # Category ID in path, e.g. q0300, b0191
    for part in path_parts:
        if re.match(r'^[a-z]\d{3,}$', part):
            params.setdefault('categoryId', part)
            break

    return params


def fetch_listings(url: str, limit: int = 30) -> list[dict]:
    """Return a list of item dicts from a Marktplaats search URL."""
    params = parse_search_url(url)
    params['limit'] = limit

    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        logger.error('Marktplaats API HTTP error: %s', e)
        raise
    except Exception as e:
        logger.error('Marktplaats API error: %s', e)
        raise

    items = []
    seen_ids: set[str] = set()

    # topBlock contains promoted listings — include them but deduplicate
    for listing in data.get('listings', []) + data.get('topBlock', []):
        item_id = str(listing.get('itemId', ''))
        if not item_id or item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        price_info = listing.get('priceInfo') or {}
        price_cents = int(price_info.get('priceCents') or 0)
        price_type = price_info.get('priceType') or 'FIXED'

        images = listing.get('imageUrls') or []
        image_url = images[0] if images else None

        location = listing.get('location') or {}
        city = location.get('cityName') or ''

        vip = listing.get('vipUrl') or ''
        full_url = f'https://www.marktplaats.nl{vip}' if vip.startswith('/') else vip

        items.append({
            'id': item_id,
            'title': listing.get('title') or '',
            'price_cents': price_cents,
            'price_type': price_type,
            'url': full_url,
            'image_url': image_url,
            'city': city,
            'date': listing.get('date') or '',
        })

    return items

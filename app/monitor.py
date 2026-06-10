import time
import sqlite3
import logging
import threading
from datetime import datetime, timezone

from db import get_conn, get_setting
from marktplaats import fetch_listings
from notifier import send_discord, send_telegram

logger = logging.getLogger(__name__)

_lock = threading.Lock()  # prevents two threads running the same search simultaneously


def _process(search: dict) -> None:
    sid = search['id']
    name = search['name']
    url = search['url']

    with _lock:
        pass  # acquire/release immediately; per-search locking not needed at this scale

    logger.info('Checking search "%s" ...', name)
    try:
        items = fetch_listings(url)
    except Exception as e:
        logger.error('Search "%s" fetch failed: %s', name, e)
        _mark_run(sid)
        return

    new_items = _store(sid, items)

    _mark_run(sid)

    if new_items:
        logger.info('Search "%s": %d new item(s) found', name, len(new_items))
        _notify(new_items, name)
    else:
        logger.info('Search "%s": no new items', name)


def _store(search_id: int, items: list[dict]) -> list[dict]:
    """
    Insert unseen items; return only the ones that are genuinely new.
    On the very first run (table empty for this search) we seed silently.
    """
    with get_conn() as conn:
        count = conn.execute(
            'SELECT COUNT(*) FROM seen_items WHERE search_id = ?', (search_id,)
        ).fetchone()[0]
        is_first_run = count == 0

        new_items = []
        for item in items:
            try:
                conn.execute(
                    'INSERT INTO seen_items '
                    '(search_id, item_id, title, price_cents, price_type, item_url, image_url, city) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        search_id,
                        item['id'],
                        item['title'],
                        item['price_cents'],
                        item['price_type'],
                        item['url'],
                        item.get('image_url'),
                        item.get('city', ''),
                    ),
                )
                if not is_first_run:
                    new_items.append(item)
            except sqlite3.IntegrityError:
                pass  # already seen

    if is_first_run:
        logger.info('Search id=%d: first run — seeded %d existing items (no notifications)', search_id, len(items))

    return new_items


def _mark_run(search_id: int) -> None:
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    with get_conn() as conn:
        conn.execute('UPDATE searches SET last_run = ? WHERE id = ?', (now, search_id))


def _notify(items: list[dict], search_name: str) -> None:
    discord_url = get_setting('discord_webhook')
    if discord_url:
        send_discord(discord_url, items, search_name)

    tg_token = get_setting('telegram_token')
    tg_chat = get_setting('telegram_chat_id')
    if tg_token and tg_chat:
        send_telegram(tg_token, tg_chat, items, search_name)


def _loop() -> None:
    last_run: dict[int, float] = {}
    while True:
        try:
            with get_conn() as conn:
                searches = conn.execute(
                    'SELECT id, name, url, interval_minutes FROM searches WHERE active = 1'
                ).fetchall()

            now = time.monotonic()
            for s in searches:
                sid = s['id']
                interval_sec = (s['interval_minutes'] or 5) * 60
                if now - last_run.get(sid, 0) >= interval_sec:
                    last_run[sid] = now
                    threading.Thread(
                        target=_process,
                        args=(dict(s),),
                        daemon=True,
                        name=f'search-{sid}',
                    ).start()
        except Exception as e:
            logger.error('Monitor loop error: %s', e)

        time.sleep(30)


def start() -> None:
    t = threading.Thread(target=_loop, daemon=True, name='monitor-loop')
    t.start()
    logger.info('Monitor started')

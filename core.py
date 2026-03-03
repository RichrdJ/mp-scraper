"""Core polling loop - runs in background threads."""

import logging
import queue
import threading
import time

import db
import telegram_plugin
from scraper import Listing, create_session, fetch_listings

logger = logging.getLogger(__name__)

_new_items_queue: queue.Queue = queue.Queue()
_stop_event = threading.Event()


def poll_loop():
    """Continuously poll all enabled search queries for new listings."""
    session = create_session()

    while not _stop_event.is_set():
        try:
            queries = db.get_queries()
            for query in queries:
                if _stop_event.is_set():
                    break
                if not query["enabled"]:
                    continue

                listings = fetch_listings(query["url"], session)
                logger.info(
                    f"Query '{query['name'] or query['url'][:60]}': "
                    f"{len(listings)} listings gevonden"
                )

                new_count = 0
                for listing in listings:
                    if not db.item_exists(listing.mp_id, query["id"]):
                        db.add_item(
                            mp_id=listing.mp_id,
                            query_id=query["id"],
                            title=listing.title,
                            price=listing.price,
                            url=listing.url,
                            image_url=listing.image_url,
                            description=listing.description,
                        )
                        _new_items_queue.put((listing, dict(query)))
                        new_count += 1

                if new_count:
                    logger.info(f"  → {new_count} nieuw")

                db.update_last_checked(query["id"])

                # Polite delay between individual queries
                _stop_event.wait(2)

        except Exception as e:
            logger.error(f"Poll loop fout: {e}", exc_info=True)

        interval = int(db.get_setting("poll_interval", "60"))
        logger.debug(f"Wachten {interval}s voor volgende ronde...")
        _stop_event.wait(interval)


def notification_loop():
    """Drain the queue and send Telegram notifications."""
    while not _stop_event.is_set():
        try:
            listing, query = _new_items_queue.get(timeout=1)
        except queue.Empty:
            continue

        try:
            token = db.get_setting("telegram_token")
            chat_id = db.get_setting("telegram_chat_id")
            if token and chat_id:
                telegram_plugin.send_notification(
                    token, chat_id, listing, query.get("name") or query.get("url", "")
                )
        except Exception as e:
            logger.error(f"Notificatie fout: {e}")


def start():
    db.init_db()
    _stop_event.clear()

    threading.Thread(target=poll_loop, daemon=True, name="poll-loop").start()
    threading.Thread(target=notification_loop, daemon=True, name="notif-loop").start()

    logger.info("Marktplaats Notifications gestart")


def stop():
    _stop_event.set()

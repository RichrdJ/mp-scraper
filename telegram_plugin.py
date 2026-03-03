"""Telegram notification plugin."""

import logging
from typing import Optional

import requests

from scraper import Listing

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def send_notification(token: str, chat_id: str, listing: Listing, query_name: str):
    caption = (
        f"*{_esc(listing.title)}*\n"
        f"💰 {_esc(listing.price)}\n"
        f"🔍 {_esc(query_name)}"
    )
    if listing.description:
        caption += f"\n\n_{_esc(listing.description[:200])}_"

    # Append link as plain text (works in all parse modes)
    caption += f"\n\n[Bekijk advertentie]({listing.url})"

    if listing.image_url:
        sent = _send_photo(token, chat_id, listing.image_url, caption)
        if sent:
            return

    _send_message(token, chat_id, caption)


def _send_photo(token: str, chat_id: str, photo_url: str, caption: str) -> bool:
    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token, method="sendPhoto"),
            json={
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "MarkdownV2",
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.debug(f"sendPhoto mislukt: {e}")
        return False


def _send_message(token: str, chat_id: str, text: str):
    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token, method="sendMessage"),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(f"Telegram fout: {resp.text}")
    except Exception as e:
        logger.error(f"sendMessage fout: {e}")


def test_connection(token: str, chat_id: str) -> tuple[bool, str]:
    """Verify token validity and send a test message."""
    try:
        resp = requests.get(
            TELEGRAM_API.format(token=token, method="getMe"), timeout=10
        )
        if resp.status_code != 200:
            return False, f"Ongeldig token: {resp.json().get('description', 'Onbekende fout')}"

        bot_name = resp.json()["result"]["username"]

        resp2 = requests.post(
            TELEGRAM_API.format(token=token, method="sendMessage"),
            json={"chat_id": chat_id, "text": "✅ Marktplaats Notifications verbonden!"},
            timeout=10,
        )
        if resp2.status_code != 200:
            return False, f"Kon geen bericht sturen: {resp2.json().get('description', 'Onbekende fout')}"

        return True, f"Verbonden als @{bot_name}"
    except Exception as e:
        return False, str(e)


def _esc(text: Optional[str]) -> str:
    """Escape MarkdownV2 special characters."""
    if not text:
        return ""
    special = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))

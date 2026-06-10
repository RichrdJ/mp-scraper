import html
import logging
import requests

logger = logging.getLogger(__name__)

MP_COLOR = 0x3a72d6


def format_price(price_cents: int, price_type: str) -> str:
    if price_type == 'NOTK':
        return 'Prijs op aanvraag'
    if price_type == 'GIVE_AWAY':
        return 'Gratis'
    if price_type in ('SEE_DESCRIPTION', 'RESERVED'):
        return price_type.replace('_', ' ').title()
    if price_cents == 0:
        return 'Bieden'
    return f'€{price_cents / 100:.2f}'.replace('.', ',')


def _discord_embed(item: dict, search_name: str) -> dict:
    price = format_price(item['price_cents'], item['price_type'])
    embed = {
        'title': item['title'][:256],
        'url': item['url'],
        'color': MP_COLOR,
        'fields': [
            {'name': 'Prijs', 'value': price, 'inline': True},
            {'name': 'Locatie', 'value': item['city'] or 'Onbekend', 'inline': True},
            {'name': 'Zoekopdracht', 'value': search_name, 'inline': True},
        ],
        'footer': {'text': 'Marktplaats Monitor'},
    }
    if item.get('image_url'):
        embed['thumbnail'] = {'url': item['image_url']}
    return embed


def send_discord(webhook_url: str, items: list[dict], search_name: str) -> None:
    for item in items:
        payload = {'embeds': [_discord_embed(item, search_name)]}
        try:
            r = requests.post(webhook_url, json=payload, timeout=10)
            r.raise_for_status()
        except Exception as e:
            logger.error('Discord notification failed for "%s": %s', item.get('title'), e)


def _tg_text(item: dict, search_name: str) -> str:
    """Build an HTML-formatted Telegram message (safer than Markdown for arbitrary titles)."""
    price = format_price(item['price_cents'], item['price_type'])
    title = html.escape(item['title'])
    city  = html.escape(item['city'] or 'Onbekend')
    sname = html.escape(search_name)
    url   = item['url']
    return (
        f'🔔 <b>{sname}</b>\n'
        f'<b>{title}</b>\n'
        f'💶 {price}\n'
        f'📍 {city}\n'
        f'<a href="{url}">Bekijk advertentie</a>'
    )


def send_telegram(token: str, chat_id: str, items: list[dict], search_name: str) -> None:
    base = f'https://api.telegram.org/bot{token}'
    for item in items:
        text = _tg_text(item, search_name)
        image_url = item.get('image_url') or ''

        # Ensure image URL is absolute
        if image_url.startswith('//'):
            image_url = 'https:' + image_url

        sent = False

        # Try sending with photo first
        if image_url:
            try:
                r = requests.post(
                    f'{base}/sendPhoto',
                    json={
                        'chat_id': chat_id,
                        'photo': image_url,
                        'caption': text,
                        'parse_mode': 'HTML',
                    },
                    timeout=15,
                )
                r.raise_for_status()
                sent = True
            except Exception as e:
                logger.warning('sendPhoto failed for "%s", falling back to text: %s', item.get('title'), e)

        # Fall back to plain text message
        if not sent:
            try:
                r = requests.post(
                    f'{base}/sendMessage',
                    json={
                        'chat_id': chat_id,
                        'text': text,
                        'parse_mode': 'HTML',
                        'disable_web_page_preview': False,
                    },
                    timeout=10,
                )
                r.raise_for_status()
            except Exception as e:
                logger.error('Telegram notification failed for "%s": %s', item.get('title'), e)

import logging
import requests

logger = logging.getLogger(__name__)

MP_COLOR = 0xff6200  # Marktplaats orange


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


def send_telegram(token: str, chat_id: str, items: list[dict], search_name: str) -> None:
    base = f'https://api.telegram.org/bot{token}'
    for item in items:
        price = format_price(item['price_cents'], item['price_type'])
        caption = (
            f'\U0001f514 *{search_name}*\n'
            f'*{item["title"]}*\n'
            f'\U0001f4b6 {price}\n'
            f'\U0001f4cd {item["city"] or "Onbekend"}\n'
            f'[Bekijk advertentie]({item["url"]})'
        )
        if item.get('image_url'):
            endpoint = f'{base}/sendPhoto'
            payload = {
                'chat_id': chat_id,
                'photo': item['image_url'],
                'caption': caption,
                'parse_mode': 'Markdown',
            }
        else:
            endpoint = f'{base}/sendMessage'
            payload = {
                'chat_id': chat_id,
                'text': caption,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False,
            }
        try:
            r = requests.post(endpoint, json=payload, timeout=10)
            r.raise_for_status()
        except Exception as e:
            logger.error('Telegram notification failed for "%s": %s', item.get('title'), e)

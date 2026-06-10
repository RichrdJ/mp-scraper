import logging
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

import log_buffer
from db import init_db, get_conn, get_setting, set_setting
from notifier import send_discord, send_telegram, format_price
import monitor

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
    datefmt='%H:%M:%S',
)
log_buffer.setup()
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'mp-monitor-change-me-in-production'


# ── Template helpers ──────────────────────────────────────────────────────────
@app.template_filter('price')
def price_filter(item) -> str:
    if isinstance(item, dict):
        return format_price(item.get('price_cents', 0), item.get('price_type', 'FIXED'))
    return ''


@app.template_filter('time_ago')
def time_ago_filter(dt_str: str) -> str:
    if not dt_str:
        return '–'
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        diff = datetime.now(timezone.utc) - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return f'{secs}s geleden'
        if secs < 3600:
            return f'{secs // 60}m geleden'
        if secs < 86400:
            return f'{secs // 3600}u geleden'
        return f'{secs // 86400}d geleden'
    except Exception:
        return dt_str


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    with get_conn() as conn:
        items = conn.execute('''
            SELECT si.title, si.price_cents, si.price_type, si.item_url,
                   si.image_url, si.city, si.first_seen, s.name AS search_name
            FROM seen_items si
            JOIN searches s ON si.search_id = s.id
            ORDER BY si.first_seen DESC
            LIMIT 60
        ''').fetchall()

        active_count = conn.execute(
            'SELECT COUNT(*) FROM searches WHERE active = 1'
        ).fetchone()[0]

        total_items = conn.execute('SELECT COUNT(*) FROM seen_items').fetchone()[0]

        today = datetime.now(timezone.utc).strftime('%Y-%m-%dT00:00:00Z')
        today_items = conn.execute(
            'SELECT COUNT(*) FROM seen_items WHERE first_seen >= ?', (today,)
        ).fetchone()[0]

    return render_template(
        'index.html',
        items=[dict(i) for i in items],
        active_count=active_count,
        total_items=total_items,
        today_items=today_items,
    )


@app.route('/searches')
def searches():
    with get_conn() as conn:
        rows = conn.execute('''
            SELECT s.*, COUNT(si.id) AS item_count
            FROM searches s
            LEFT JOIN seen_items si ON s.id = si.search_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        ''').fetchall()
    return render_template('searches.html', searches=[dict(r) for r in rows])


@app.route('/searches/add', methods=['POST'])
def add_search():
    name = request.form.get('name', '').strip()
    url = request.form.get('url', '').strip()
    try:
        interval = max(1, int(request.form.get('interval', 5)))
    except ValueError:
        interval = 5

    if not name or not url:
        flash('Naam en URL zijn verplicht.', 'danger')
        return redirect(url_for('searches'))

    if 'marktplaats.nl' not in url:
        flash('Voer een geldige Marktplaats-URL in.', 'danger')
        return redirect(url_for('searches'))

    with get_conn() as conn:
        conn.execute(
            'INSERT INTO searches (name, url, interval_minutes, active) VALUES (?, ?, ?, 1)',
            (name, url, interval),
        )

    flash(f'Zoekopdracht "{name}" toegevoegd.', 'success')
    return redirect(url_for('searches'))


@app.route('/searches/<int:sid>/toggle', methods=['POST'])
def toggle_search(sid: int):
    with get_conn() as conn:
        row = conn.execute('SELECT active FROM searches WHERE id = ?', (sid,)).fetchone()
        if row:
            conn.execute('UPDATE searches SET active = ? WHERE id = ?', (1 - row['active'], sid))
    return redirect(url_for('searches'))


@app.route('/searches/<int:sid>/reset', methods=['POST'])
def reset_search(sid: int):
    """Delete seen items so the next run seeds fresh (without sending notifications)."""
    with get_conn() as conn:
        conn.execute('DELETE FROM seen_items WHERE search_id = ?', (sid,))
    flash('Geziene items gewist. De volgende run zaait opnieuw in.', 'info')
    return redirect(url_for('searches'))


@app.route('/searches/<int:sid>/delete', methods=['POST'])
def delete_search(sid: int):
    with get_conn() as conn:
        conn.execute('DELETE FROM searches WHERE id = ?', (sid,))
    flash('Zoekopdracht verwijderd.', 'success')
    return redirect(url_for('searches'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        set_setting('discord_webhook', request.form.get('discord_webhook', '').strip())
        set_setting('telegram_token', request.form.get('telegram_token', '').strip())
        set_setting('telegram_chat_id', request.form.get('telegram_chat_id', '').strip())
        flash('Instellingen opgeslagen.', 'success')
        return redirect(url_for('settings'))

    return render_template(
        'settings.html',
        discord_webhook=get_setting('discord_webhook'),
        telegram_token=get_setting('telegram_token'),
        telegram_chat_id=get_setting('telegram_chat_id'),
    )


# ── API endpoints (used by the frontend via fetch) ────────────────────────────
@app.route('/api/logs')
def api_logs():
    return jsonify(log_buffer.get_recent())


@app.route('/api/test/discord', methods=['POST'])
def api_test_discord():
    webhook = get_setting('discord_webhook')
    if not webhook:
        return jsonify({'error': 'Geen Discord webhook ingesteld.'}), 400
    try:
        send_discord(webhook, [_test_item()], 'Test')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/telegram', methods=['POST'])
def api_test_telegram():
    token = get_setting('telegram_token')
    chat_id = get_setting('telegram_chat_id')
    if not token or not chat_id:
        return jsonify({'error': 'Telegram token of chat-ID ontbreekt.'}), 400
    try:
        send_telegram(token, chat_id, [_test_item()], 'Test')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _test_item() -> dict:
    return {
        'title': 'Test advertentie — Marktplaats Monitor',
        'price_cents': 4999,
        'price_type': 'FIXED',
        'url': 'https://www.marktplaats.nl',
        'image_url': None,
        'city': 'Amsterdam',
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    monitor.start()
    logger.info('Web interface running on http://0.0.0.0:8000')
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)

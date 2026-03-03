# 🏪 Marktplaats Notifications

Automatically monitor [Marktplaats.nl](https://www.marktplaats.nl) search results and receive instant **Telegram notifications** — with photo, price and a direct link.

---

## ✨ Features

- **Web UI** on port `7070` — clean dashboard to manage everything
- **Multiple search queries** running simultaneously
- **Telegram notifications** with photo, price and link for every new listing
- **Configurable polling interval** — choose how often Marktplaats is checked
- **Persistent storage** via Docker volume (SQLite)
- Filtered search URLs supported (price range, category, etc.)

---

## 🚀 Quick start

### Docker Compose

```bash
git clone https://github.com/RichrdJ/mp-scraper.git
cd mp-scraper
docker compose up -d --build
```

Then open **http://localhost:7070** in your browser.

---

### Portainer (Stack)

1. Go to **Stacks → Add stack**
2. Give it a name (e.g. `marktplaats`)
3. Paste the following YAML:

```yaml
version: "3.8"

services:
  marktplaats-notifications:
    build:
      context: https://github.com/RichrdJ/mp-scraper.git
    container_name: marktplaats-notifications
    ports:
      - "7070:7070"
    volumes:
      - mp_data:/app/data
    environment:
      - DB_PATH=/app/data/marktplaats.db
    restart: unless-stopped

volumes:
  mp_data:
```

4. Click **Deploy the stack**

> **Updating:** Always remove the old image under **Images** in Portainer before redeploying, otherwise Docker will use the cached version.

---

## ⚙️ Configuration

### 1. Add a search query

Go to **Search queries** in the web UI and paste a Marktplaats search URL.

Examples:

| Search | URL |
|---|---|
| iPhone 14 | `https://www.marktplaats.nl/q/iphone+14/` |
| Laptops under €500 | `https://www.marktplaats.nl/l/computers-en-software/laptops/#PriceCentsTo:50000` |
| Free bicycles | `https://www.marktplaats.nl/q/fiets/#f:for-sale,price:0` |
| Specific category | `https://www.marktplaats.nl/l/audio-tv-en-foto/` |

Just copy the URL from your browser after searching — filters included.

### 2. Set up Telegram

1. Create a bot via [@BotFather](https://t.me/BotFather) → `/newbot` → copy the **token**
2. Find your **Chat ID** via [@userinfobot](https://t.me/userinfobot)
3. Enter both under **Settings** in the web UI
4. Click **"Send test message"** to verify the connection

---

## 📁 Project structure

```
mp-scraper/
├── main.py               # Entry point (Flask + polling)
├── core.py               # Polling loop (background threads)
├── scraper.py            # Marktplaats.nl scraper
├── db.py                 # SQLite database
├── telegram_plugin.py    # Telegram notifications
├── web_ui/
│   ├── __init__.py       # Flask routes
│   └── templates/        # HTML pages
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🔄 Updating

```bash
git pull
docker compose up -d --build --no-cache
```

Or in Portainer: **Images → remove old image → Stacks → Redeploy**

---

## 🛠️ Tech stack

- **Python 3.11** · Flask · Requests · BeautifulSoup4
- **SQLite** for storage
- **Telegram Bot API** for notifications
- **Docker** for deployment

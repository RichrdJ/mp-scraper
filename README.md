# 🏪 Marktplaats Notifications

Automatisch nieuwe advertenties op [Marktplaats.nl](https://www.marktplaats.nl) monitoren en direct een **Telegram-notificatie** ontvangen — met foto, prijs en directe link.

---

## ✨ Functies

- **Web UI** op poort `7070` — overzichtelijk dashboard
- **Meerdere zoekopdrachten** tegelijk bijhouden
- **Telegram-notificaties** met foto, prijs en link bij elke nieuwe advertentie
- **Instelbaar interval** — hoe vaak Marktplaats gecheckt wordt
- **Persistente opslag** via Docker volume (SQLite)
- Gefilterde zoek-URL's worden ondersteund (prijs, categorie, enz.)

---

## 🚀 Snel starten

### Via Docker Compose

```bash
git clone https://github.com/RichrdJ/mp-scraper.git
cd mp-scraper
docker compose up -d --build
```

Open daarna **http://localhost:7070** in je browser.

---

### Via Portainer (Stack)

1. Ga naar **Stacks → Add stack**
2. Geef de stack een naam (bv. `marktplaats`)
3. Plak onderstaande YAML:

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

4. Klik **Deploy the stack**

> **Let op bij updates:** Verwijder eerst de oude image via **Images** in Portainer voordat je opnieuw deployt, anders gebruikt Docker de gecachede versie.

---

## ⚙️ Configuratie

### 1. Zoekopdracht toevoegen

Ga naar **Zoekopdrachten** in de web UI en plak een Marktplaats zoek-URL.

Voorbeelden:

| Zoekterm | URL |
|---|---|
| iPhone 14 | `https://www.marktplaats.nl/q/iphone+14/` |
| Laptops onder €500 | `https://www.marktplaats.nl/l/computers-en-software/laptops/#PriceCentsTo:50000` |
| Gratis fietsen | `https://www.marktplaats.nl/q/fiets/#f:for-sale,price:0` |
| Specifieke categorie | `https://www.marktplaats.nl/l/audio-tv-en-foto/` |

Kopieer gewoon de URL uit je browser na het zoeken — inclusief filters.

### 2. Telegram instellen

1. Maak een bot aan via [@BotFather](https://t.me/BotFather) → `/newbot` → kopieer het **token**
2. Vind je **Chat ID** via [@userinfobot](https://t.me/userinfobot)
3. Vul beide in via **Instellingen** in de web UI
4. Klik **"Verstuur testbericht"** om te controleren

---

## 📁 Projectstructuur

```
mp-scraper/
├── main.py               # Startpunt (Flask + polling)
├── core.py               # Polling loop (achtergrond-threads)
├── scraper.py            # Marktplaats.nl scraper
├── db.py                 # SQLite database
├── telegram_plugin.py    # Telegram notificaties
├── web_ui/
│   ├── __init__.py       # Flask routes
│   └── templates/        # HTML pagina's
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🔄 Updaten

```bash
git pull
docker compose up -d --build --no-cache
```

Of in Portainer: **Images → verwijder oude image → Stacks → Redeploy**

---

## 🛠️ Tech stack

- **Python 3.11** · Flask · Requests · BeautifulSoup4
- **SQLite** voor opslag
- **Telegram Bot API** voor notificaties
- **Docker** voor deployment

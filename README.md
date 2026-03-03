# Marktplaats Notifications

Monitort Marktplaats.nl zoekresultaten en stuurt Telegram-notificaties bij nieuwe advertenties.

## Functies

- Web UI op poort **7070**
- Meerdere zoekopdrachten tegelijk
- Telegram-notificaties met foto, prijs en link
- Instelbaar polling-interval
- SQLite database (persistent via Docker volume)

## Starten met Docker

```bash
docker compose up -d --build
```

Open daarna **http://\<ip\>:7070** in je browser.

## Starten in Portainer (Stack)

Plak dit als nieuwe stack in Portainer:

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

## Configuratie

1. Ga naar **Zoekopdrachten** en voeg een Marktplaats zoek-URL toe
   (bv. `https://www.marktplaats.nl/q/iphone+14/`)
2. Ga naar **Instellingen** en vul in:
   - **Telegram Bot Token** — aanmaken via [@BotFather](https://t.me/BotFather)
   - **Chat ID** — opvragen via [@userinfobot](https://t.me/userinfobot)
3. Klik **"Verstuur testbericht"** om de verbinding te testen

## Update naar nieuwste versie

In Portainer: **Stacks → Update the stack → Re-pull image and redeploy**

Of via SSH:
```bash
docker compose pull && docker compose up -d --build
```

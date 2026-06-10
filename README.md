<div align="center">
  <img src="https://raw.githubusercontent.com/RichrdJ/mp-scraper/main/docs/banner.svg" alt="Marktplaats Monitor" width="100%"/>
</div>

<br>

<div align="center">
  <a href="https://github.com/RichrdJ/mp-scraper/releases"><img src="https://img.shields.io/github/v/release/RichrdJ/mp-scraper?color=3a72d6&label=release&style=flat-square" alt="Release"/></a>
  <a href="https://github.com/RichrdJ/mp-scraper/pkgs/container/mp-scraper"><img src="https://img.shields.io/badge/ghcr.io-mp--scraper-3a72d6?style=flat-square&logo=docker&logoColor=white" alt="Docker"/></a>
  <a href="https://github.com/RichrdJ/mp-scraper/actions"><img src="https://img.shields.io/github/actions/workflow/status/RichrdJ/mp-scraper/docker.yml?style=flat-square&label=build&color=3a72d6" alt="Build"/></a>
</div>

<br>

Nooit meer een koopje missen op Marktplaats. Stel zoekopdrachten in en ontvang direct een melding zodra er een nieuwe advertentie verschijnt — via Discord, Telegram of gewoon in de webinterface.

---

## ✨ Functies

- **Realtime monitoring** — checkt je zoekopdrachten op instelbaar interval (standaard 5 min)
- **Alleen nieuwe advertenties** — de eerste run zaait bestaande items in zonder meldingen, daarna krijg je enkel wat er nieuw bijkomt
- **Discord & Telegram** — rijke meldingen met foto, prijs en locatie
- **Webinterface met dark mode** — overzichtelijk dashboard, zoekopdrachten beheren en instellingen
- **Docker-ready** — één `docker-compose.yml` en je bent live
- **Persistente opslag** — SQLite met WAL-mode, data overleeft container-restarts

---

## 🚀 Snel starten

### Vereisten
- Docker + Docker Compose

### 1. Maak een `docker-compose.yml`

```yaml
services:
  marktplaats-monitor:
    image: ghcr.io/richrdj/mp-scraper:latest
    pull_policy: always
    container_name: marktplaats-monitor
    ports:
      - "8000:8000"
    volumes:
      - mp_data:/data
    restart: unless-stopped

volumes:
  mp_data:
```

### 2. Start de container

```bash
docker compose up -d
```

### 3. Open de webinterface

Ga naar `http://localhost:8000` (of het IP van je server).

---

## ⚙️ Configuratie

Alle instellingen zijn te beheren via de webinterface onder **Instellingen**:

| Instelling | Beschrijving |
|---|---|
| Discord Webhook URL | Maak aan via Kanaalinstellingen → Integraties → Webhooks |
| Telegram Bot Token | Aanmaken via [@BotFather](https://t.me/BotFather) |
| Telegram Chat ID | Opvragen via [@userinfobot](https://t.me/userinfobot) |

---

## 🔍 Zoekopdrachten toevoegen

1. Ga naar [marktplaats.nl](https://www.marktplaats.nl) en stel je zoekopdracht en filters in
2. Kopieer de volledige URL uit de adresbalk (inclusief `#`-gedeelte met filters)
3. Plak de URL in de webinterface onder **Zoekopdrachten → Nieuwe zoekopdracht**

**Ondersteunde URL-formaten:**
```
https://www.marktplaats.nl/q/iphone+13/
https://www.marktplaats.nl/q/macbook/#priceFrom=500&priceTo=1500
https://www.marktplaats.nl/l/computers-en-software/laptops/q0300/#query=dell
```

---

## 📬 Meldingen

### Discord
Meldingen verschijnen als embed met foto, prijs, locatie en een directe link naar de advertentie.

### Telegram
Stuurt een foto-bericht (als beschikbaar) met prijs, locatie en een klikbare link.

> **Tip:** Gebruik de **Test**-knop in de instellingen om te controleren of meldingen correct binnenkomen.

---

## 🛠️ Zelf bouwen

```bash
git clone https://github.com/RichrdJ/mp-scraper.git
cd mp-scraper
docker compose up -d --build
```

---

## 📦 Stack

| Onderdeel | Technologie |
|---|---|
| Backend | Python 3.12 + Flask |
| Database | SQLite (WAL-mode) |
| Meldingen | Discord Webhooks · Telegram Bot API |
| Frontend | Bootstrap 5.3 + Bootstrap Icons |
| Container | Docker / Docker Compose |
| CI/CD | GitHub Actions → GHCR |

---

## 📄 Licentie

MIT — doe er mee wat je wilt.

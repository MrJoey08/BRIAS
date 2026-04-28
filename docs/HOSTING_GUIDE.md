# BRIAS — Hosting Guide

## Jouw situatie
- Frontend: momenteel op Vercel (gratis tier)
- Backend: FastAPI, draait lokaal op Windows
- Domein: brias.eu (wil later brias.ai)
- Code: GitHub

## Het probleem
BRIAS heeft een backend nodig die **altijd draait** — haar kernloop denkt continu, ook als niemand chat. Dat maakt serverless (Vercel Functions, AWS Lambda) ongeschikt: die slapen als er geen requests zijn.

## Mijn aanbeveling: Render.com

### Waarom Render?
- **Gratis tier**: 750 uur/maand web service (genoeg voor 1 always-on service)
- **FastAPI support**: native Python, deploy via GitHub push
- **Gratis PostgreSQL**: 30 dagen (daarna ~$7/maand, of gebruik SQLite op disk)
- **Simple**: git push → deployed. Geen Docker kennis nodig.
- **Gratis SSL**: automatisch HTTPS
- **Custom domain**: brias.eu koppelen is gratis

### Het nadeel van de gratis tier
De gratis web service "spint down" na 15 min inactiviteit. Dat is een probleem voor BRIAS want haar kernloop moet altijd draaien. Oplossingen:

1. **Zelf-ping**: Een simpel cron job (via cron-job.org, gratis) die elke 14 min een request naar je backend stuurt → ze blijft wakker
2. **Starter plan ($7/maand)**: Always-on, geen spin-down. Dit is de beste optie zodra je serieus gaat.

### Alternatieve opties

| Platform | Gratis tier | Prijs daarna | Voordeel | Nadeel |
|---|---|---|---|---|
| **Render** | 750 uur/maand | $7/maand starter | Simpelst, FastAPI native | Spint down op gratis tier |
| **Railway** | $5 eenmalig credit | ~$5-10/maand | Snelle deploys, mooie UI | Geen echte gratis tier |
| **Fly.io** | 3 shared VMs gratis | ~$5/maand | Wereldwijd, snel | Complexere setup |
| **Oracle Cloud** | Always Free VPS | Gratis (echt) | Gratis VPS forever, 1GB RAM | Complexe setup, Oracle UI |
| **Hetzner VPS** | Geen | €4.51/maand | Snelste voor de prijs, EU servers | Zelf beheren (Linux kennis) |
| **Vercel (huidig)** | Frontend gratis | - | Je gebruikt het al | Geen backend support |

### Mijn aanbevolen setup

**Nu (gratis):**
- Frontend: **Vercel** (je hebt dit al, werkt prima)
- Backend: **Render free tier** + cron-job.org ping
- Database: SQLite (file-based, geen extra service nodig)
- Domein: brias.eu → Vercel (frontend) + api.brias.eu → Render (backend)

**Later (als het serieuzer wordt, ~$7-11/maand):**
- Frontend: Vercel (blijft gratis)
- Backend: Render Starter ($7/maand, always-on)
- Database: Render PostgreSQL ($7/maand) OF blijf bij SQLite
- Domein: brias.eu (later brias.ai als het betaalbaar wordt)

**Lange termijn (als BRIAS echt groeit):**
- Hetzner VPS (€4.51/maand voor 2 vCPU, 4GB RAM) — volledige controle
- Of Railway/Render op hogere tier

## Render setup stappen

1. Maak een account op render.com
2. Verbind je GitHub
3. New → Web Service → selecteer je BRIAS repo
4. Settings:
   - Runtime: Python 3
   - Build command: `pip install -r brain/requirements.txt`
   - Start command: `cd brain && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment variables toevoegen (uit .env)
6. Deploy!

## Over brias.ai
Het .ai domein is momenteel duur (~$80-100/jaar). brias.eu is prima voor nu. Je kunt later altijd switchen — zorg er alleen voor dat je frontend niet hard-coded naar brias.eu verwijst maar een environment variable gebruikt voor de URL.

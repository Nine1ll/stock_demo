# Render Deployment Guide

## 1) Push code to GitHub
This repository must be on GitHub first.

## 2) Create Web Service on Render
1. Render dashboard -> `New +` -> `Web Service`
2. Connect GitHub repo: `Nine1ll/stock_demo`
3. Render will detect `render.yaml` automatically (Blueprint)  
   or create manually with:
   - Runtime: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python web_server.py --host 0.0.0.0 --port $PORT`

## 3) Set environment variables
Add in Render dashboard (`Environment`):
- `FINNHUB_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `SEC_USER_AGENT`
- `DART_API_KEY` (optional, KR filings)
- `OPENAI_API_KEY` (optional)
- `OPENAI_MODEL` (optional, default `gpt-4.1-mini`)
- `ALERT_POLL_SECONDS` (optional, default `300`)

## 4) Deploy and verify
- App URL: `https://<your-service>.onrender.com/web/index.html`
- Health: `https://<your-service>.onrender.com/api/health`

## 5) Notes (important)
- Free plan sleeps on inactivity, so first request can be slow.
- Filesystem is ephemeral on free plan:
  - `data/stock_app.db` can reset on redeploy/restart.
  - For persistent data, use paid persistent disk or external DB.

# Oracle Always Free Deployment Guide

This app needs a Python backend (`web_server.py`), so deploy it to a VM for always-on access.

## 1. Create VM
- Provider: Oracle Cloud Free Tier
- Shape: Always Free eligible (Ubuntu)
- Open inbound rules:
  - `22/tcp` (SSH)
  - `8000/tcp` (App)

Reference: Oracle Always Free resources  
https://docs.oracle.com/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## 2. SSH and clone
```bash
ssh ubuntu@<YOUR_VM_PUBLIC_IP>
git clone <YOUR_REPO_URL> stock-intel
cd stock-intel
```

## 3. Configure `.env`
```bash
cp .env.example .env
nano .env
```
Fill real API keys and settings as needed.

## 4. Run one-shot setup
```bash
bash deploy/oracle/setup_oci_free.sh
```

This script:
- installs Python runtime packages
- creates `.venv`
- installs dependencies
- creates and enables `systemd` service (`stock-intel`)
- opens `8000/tcp` if `ufw` exists

## 5. Verify
```bash
sudo systemctl status stock-intel
sudo journalctl -u stock-intel -f
```

Open:
- `http://<YOUR_VM_PUBLIC_IP>:8000/web/index.html`
- `http://<YOUR_VM_PUBLIC_IP>:8000/api/health`

## 6. Operations
- Restart: `sudo systemctl restart stock-intel`
- Stop: `sudo systemctl stop stock-intel`
- Start: `sudo systemctl start stock-intel`

## 7. Security notes
- Keep API keys only in `.env` on VM (never commit keys).
- Restrict `22/tcp` source IP in cloud security list if possible.
- For production, prefer HTTPS + reverse proxy (Caddy/Nginx) and domain.

## 8. HTTPS + Domain (Caddy, optional but recommended)
1. DNS
- Add `A` record: `your-domain` -> VM public IP

2. Open inbound ports
- Oracle Security List / NSG: `80/tcp`, `443/tcp` allow
- VM firewall (`ufw`) is handled by script

3. Run script
```bash
cd stock-intel
DOMAIN=stock.example.com EMAIL=you@example.com bash deploy/oracle/setup_caddy_https.sh
```

4. Verify
- `https://stock.example.com/web/index.html`
- `https://stock.example.com/api/health`

Notes:
- Script file: `deploy/oracle/setup_caddy_https.sh`
- Upstream defaults to `127.0.0.1:8000` (your Python service)

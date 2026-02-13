#!/usr/bin/env bash
set -euo pipefail

# HTTPS reverse proxy setup with Caddy.
# Prerequisites:
# - stock-intel app service is already running on localhost:8000
# - DNS A record points DOMAIN to this VM public IP
#
# Usage:
#   DOMAIN=example.com EMAIL=you@example.com bash deploy/oracle/setup_caddy_https.sh
# Optional:
#   APP_UPSTREAM=127.0.0.1:8000

DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
APP_UPSTREAM="${APP_UPSTREAM:-127.0.0.1:8000}"
APP_PORT="${APP_PORT:-8000}"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Set DOMAIN and EMAIL first."
  echo "Example: DOMAIN=stock.example.com EMAIL=ops@example.com bash deploy/oracle/setup_caddy_https.sh"
  exit 1
fi

echo "[1/6] Installing Caddy..."
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends caddy

echo "[2/6] Writing Caddyfile..."
TMP_CADDY="$(mktemp)"
cat > "$TMP_CADDY" <<EOF
{
  email $EMAIL
}

$DOMAIN {
  encode zstd gzip

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "SAMEORIGIN"
    Referrer-Policy "strict-origin-when-cross-origin"
  }

  reverse_proxy $APP_UPSTREAM
}
EOF
sudo mv "$TMP_CADDY" /etc/caddy/Caddyfile
sudo chown root:root /etc/caddy/Caddyfile
sudo chmod 644 /etc/caddy/Caddyfile

echo "[3/6] Validating Caddy config..."
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile

echo "[4/6] Opening firewall ports..."
if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 80/tcp || true
  sudo ufw allow 443/tcp || true
  # optional: close direct app port after proxy is active
  sudo ufw delete allow "${APP_PORT}/tcp" >/dev/null 2>&1 || true
fi

echo "[5/6] Enabling Caddy..."
sudo systemctl daemon-reload
sudo systemctl enable caddy
sudo systemctl restart caddy

echo "[6/6] Checking status..."
sudo systemctl --no-pager --full status caddy | sed -n '1,14p' || true

echo ""
echo "Done."
echo "- HTTPS URL: https://$DOMAIN/web/index.html"
echo "- Health:    https://$DOMAIN/api/health"
echo ""
echo "If cert issuance fails, verify:"
echo "1) DNS A record for $DOMAIN points to this VM public IP"
echo "2) inbound 80/443 is open in Oracle Security List + VM firewall"

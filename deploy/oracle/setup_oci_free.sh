#!/usr/bin/env bash
set -euo pipefail

# Oracle Cloud Always Free (Ubuntu) quick setup script.
# Usage:
#   bash deploy/oracle/setup_oci_free.sh
# Optional env:
#   APP_DIR=/home/ubuntu/stock-intel
#   APP_USER=ubuntu
#   APP_GROUP=ubuntu
#   APP_PORT=8000

APP_DIR="${APP_DIR:-$(pwd)}"
APP_USER="${APP_USER:-$(id -un)}"
APP_GROUP="${APP_GROUP:-$(id -gn)}"
APP_PORT="${APP_PORT:-8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
SERVICE_NAME="${SERVICE_NAME:-stock-intel}"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"

if [[ ! -f "$APP_DIR/web_server.py" ]]; then
  echo "web_server.py not found in APP_DIR: $APP_DIR"
  exit 1
fi

echo "[1/7] Installing OS packages..."
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends "$PYTHON_BIN" "${PYTHON_BIN}-venv" ca-certificates curl

echo "[2/7] Creating virtual environment..."
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel setuptools

echo "[3/7] Installing Python dependencies..."
if [[ -f "$APP_DIR/requirements.txt" ]]; then
  "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
fi

echo "[4/7] Preparing environment file..."
if [[ ! -f "$ENV_FILE" && -f "$APP_DIR/.env.example" ]]; then
  cp "$APP_DIR/.env.example" "$ENV_FILE"
fi
chmod 600 "$ENV_FILE" 2>/dev/null || true

echo "[5/7] Writing systemd service..."
TMP_SERVICE="$(mktemp)"
cat > "$TMP_SERVICE" <<EOF
[Unit]
Description=Stock Intel Web Server
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=-$ENV_FILE
Environment=APP_PORT=$APP_PORT
ExecStart=$VENV_DIR/bin/python $APP_DIR/web_server.py --host 0.0.0.0 --port $APP_PORT
Restart=always
RestartSec=2
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
sudo mv "$TMP_SERVICE" "$SERVICE_PATH"
sudo chmod 644 "$SERVICE_PATH"

echo "[6/7] Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "[7/7] Configuring firewall..."
if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow "${APP_PORT}/tcp" || true
fi

echo ""
echo "Done."
echo "- Service name: $SERVICE_NAME"
echo "- Status:       sudo systemctl status $SERVICE_NAME"
echo "- Logs:         sudo journalctl -u $SERVICE_NAME -f"
echo "- URL:          http://<YOUR_VM_PUBLIC_IP>:${APP_PORT}/web/index.html"

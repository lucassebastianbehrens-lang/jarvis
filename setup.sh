#!/usr/bin/env bash
# Jarvis Trading-Server – automatische Einrichtung (Ubuntu 24.04)
# Freqtrade im TEST-Modus (Spielgeld 1.000 EUR), Kraken, EUR-Paare, https über Caddy.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
[ "$(id -u)" = 0 ] || { echo "Bitte als root ausführen."; exit 1; }

echo ">> 1/6 System aktualisieren"
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq curl ufw gpg debian-keyring debian-archive-keyring apt-transport-https openssl

echo ">> 2/6 Docker installieren"
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh

echo ">> 3/6 Caddy (https) installieren"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq && apt-get install -y -qq caddy
fi

echo ">> 4/6 Firewall"
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo ">> 5/6 Freqtrade einrichten"
mkdir -p /root/ft && cd /root/ft
curl -fsSL https://raw.githubusercontent.com/freqtrade/freqtrade/stable/docker-compose.yml -o docker-compose.yml
docker compose pull -q
[ -d user_data/strategies ] || docker compose run --rm freqtrade create-userdir --userdir user_data

IP=$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
DOMAIN="${IP//./-}.sslip.io"
PASS=$(openssl rand -hex 12)
if [ ! -f user_data/config.json ]; then
cat > user_data/config.json <<EOF
{
  "bot_name": "jarvis-bot",
  "max_open_trades": 3,
  "stake_currency": "EUR",
  "stake_amount": 50,
  "tradable_balance_ratio": 0.99,
  "fiat_display_currency": "EUR",
  "dry_run": true,
  "dry_run_wallet": 1000,
  "cancel_open_orders_on_exit": false,
  "trading_mode": "spot",
  "initial_state": "running",
  "unfilledtimeout": {"entry": 10, "exit": 10, "exit_timeout_count": 0, "unit": "minutes"},
  "entry_pricing": {"price_side": "same", "use_order_book": true, "order_book_top": 1, "price_last_balance": 0.0,
    "check_depth_of_market": {"enabled": false, "bids_to_ask_delta": 1}},
  "exit_pricing": {"price_side": "same", "use_order_book": true, "order_book_top": 1},
  "exchange": {"name": "kraken", "key": "", "secret": "", "ccxt_config": {}, "ccxt_async_config": {},
    "pair_whitelist": ["BTC/EUR", "ETH/EUR", "SOL/EUR", "XRP/EUR", "ADA/EUR"], "pair_blacklist": []},
  "pairlists": [{"method": "StaticPairList"}],
  "telegram": {"enabled": false, "token": "", "chat_id": ""},
  "api_server": {"enabled": true, "listen_ip_address": "0.0.0.0", "listen_port": 8080, "verbosity": "error",
    "enable_openapi": false, "jwt_secret_key": "$(openssl rand -hex 32)", "ws_token": "$(openssl rand -hex 16)",
    "CORS_origins": ["https://lucassebastianbehrens-lang.github.io"], "username": "lucas", "password": "$PASS"},
  "internals": {"process_throttle_secs": 5}
}
EOF
else
  PASS=$(grep -o '"password": *"[^"]*"' user_data/config.json | cut -d'"' -f4)
fi
docker compose up -d

echo ">> 6/6 https-Adresse einrichten"
printf '%s {\n  reverse_proxy 127.0.0.1:8080\n}\n' "$DOMAIN" > /etc/caddy/Caddyfile
systemctl restart caddy

cat > /root/jarvis-bot-zugang.txt <<EOF
Adresse:  https://$DOMAIN
Benutzer: lucas
Passwort: $PASS
EOF
echo
echo "=============== FERTIG ==============="
cat /root/jarvis-bot-zugang.txt
echo "======================================"
echo "Diese 3 Zeilen in Jarvis > Trading > Bot-Server eintragen."
echo "Der Bot läuft im TEST-Modus mit 1.000 EUR Spielgeld."
echo "Zugang später nochmal anzeigen: cat /root/jarvis-bot-zugang.txt"

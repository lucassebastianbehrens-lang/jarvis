#!/usr/bin/env bash
# Jarvis Trading-Server – automatische Einrichtung (Ubuntu 24.04)
# Freqtrade + Agenten-Bot im TEST-Modus (Spielgeld), https über Caddy.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
[ "$(id -u)" = 0 ] || { echo "Bitte als root ausführen."; exit 1; }

echo ">> 1/7 System aktualisieren"
apt-get update -qq && apt-get upgrade -y -qq
apt-get install -y -qq curl ufw gpg debian-keyring debian-archive-keyring apt-transport-https openssl

echo ">> 2/7 Docker installieren"
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh

echo ">> 3/7 Caddy (https) installieren"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq && apt-get install -y -qq caddy
fi

echo ">> 4/7 Firewall"
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

echo ">> 5/7 Freqtrade einrichten"
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
  "max_open_trades": 6,
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
    "pair_whitelist": ["BTC/EUR", "ETH/EUR", "SOL/EUR", "XRP/EUR", "ADA/EUR", "DOGE/EUR", "DOT/EUR", "LINK/EUR", "AVAX/EUR", "LTC/EUR", "TRX/EUR", "ATOM/EUR", "BCH/EUR", "XLM/EUR", "NEAR/EUR", "SHIB/EUR", "PEPE/EUR", "POL/EUR", "SUI/EUR", "UNI/EUR"], "pair_blacklist": []},
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

echo ">> 6/7 Agenten-Bot (Memecoins, Spielgeld) einrichten"
mkdir -p /opt/jarvis /var/lib/jarvis/agents /etc/jarvis
[ -f /etc/jarvis/telegram.env ] || printf '# Telegram-Benachrichtigungen (optional)\n# TG_TOKEN=123456:ABC...\n# TG_CHAT=123456789\n' > /etc/jarvis/telegram.env
chmod 600 /etc/jarvis/telegram.env
curl -fsSL https://lucassebastianbehrens-lang.github.io/jarvis/bot/agents.py -o /opt/jarvis/agents.py
chmod 755 /var/lib/jarvis /var/lib/jarvis/agents
cat > /etc/systemd/system/jarvis-agents.service <<'SVC'
[Unit]
Description=Jarvis Agenten-Bot (Papierhandel)
After=network-online.target
[Service]
ExecStart=/usr/bin/python3 /opt/jarvis/agents.py
Restart=always
RestartSec=10
UMask=0022
[Install]
WantedBy=multi-user.target
SVC
systemctl daemon-reload
systemctl enable --now jarvis-agents

echo ">> Jarvis live (Telegram, rund um die Uhr)"
if ! grep -q '^TG_TOKEN=' /etc/jarvis/telegram.env && [ -r /dev/tty ]; then
  echo "Telegram-Bot-Token einfügen (steht in GitHub > Settings > Secrets als TG_TOKEN bzw. bei @BotFather), Enter = später:"
  read -r T </dev/tty || T=""
  if [ -n "$T" ]; then
    echo "Deine Telegram-Chat-ID (Zahl, Jarvis-App > Einstellungen > Telegram):"; read -r C </dev/tty || C=""
    echo "Groq-API-Schlüssel (optional, Enter = ohne):"; read -r G </dev/tty || G=""
    { echo "TG_TOKEN=$T"; echo "TG_CHAT=$C"; [ -n "$G" ] && echo "GROQ_KEY=$G"; } >> /etc/jarvis/telegram.env
  fi
fi
curl -fsSL https://raw.githubusercontent.com/lucassebastianbehrens-lang/jarvis/main/bot/jarvis_live.py -o /opt/jarvis/jarvis_live.py
cat > /etc/systemd/system/jarvis-live.service <<'SVC'
[Unit]
Description=Jarvis live (Telegram)
After=network-online.target
[Service]
EnvironmentFile=-/etc/jarvis/telegram.env
ExecStart=/usr/bin/python3 /opt/jarvis/jarvis_live.py
Restart=always
RestartSec=10
UMask=0022
[Install]
WantedBy=multi-user.target
SVC
sed -i 's#^ExecStart=/usr/bin/python3 /opt/jarvis/agents.py#EnvironmentFile=-/etc/jarvis/telegram.env\nExecStart=/usr/bin/python3 /opt/jarvis/agents.py#' /etc/systemd/system/jarvis-agents.service
cat > /usr/local/bin/jarvis-update <<'UPD'
#!/usr/bin/env bash
# holt neue Versionen von GitHub und startet nur bei Änderungen neu
R=https://raw.githubusercontent.com/lucassebastianbehrens-lang/jarvis/main/bot
for f in agents.py:jarvis-agents jarvis_live.py:jarvis-live; do
  n=${f%%:*}; s=${f##*:}
  curl -fsSL "$R/$n" -o "/tmp/$n" && python3 -m py_compile "/tmp/$n" && ! cmp -s "/tmp/$n" "/opt/jarvis/$n" && cp "/tmp/$n" "/opt/jarvis/$n" && systemctl restart "$s"
done
exit 0
UPD
chmod 755 /usr/local/bin/jarvis-update
echo '*/30 * * * * root /usr/local/bin/jarvis-update >/dev/null 2>&1' > /etc/cron.d/jarvis-update
echo '17 4 * * 0 root apt-get update -qq && apt-get upgrade -y -qq >/dev/null 2>&1' > /etc/cron.d/jarvis-system
systemctl daemon-reload
systemctl enable --now jarvis-live
systemctl restart jarvis-agents

echo ">> 7/7 https-Adresse einrichten"
cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
  handle /agents/* {
    header Access-Control-Allow-Origin "https://lucassebastianbehrens-lang.github.io"
    header Cache-Control "no-store"
    root * /var/lib/jarvis
    file_server
  }
  handle {
    reverse_proxy 127.0.0.1:8080
  }
}
CADDY
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
echo "Beide Bots laufen im TEST-Modus mit je 1.000 EUR Spielgeld:"
echo " - Freqtrade (20 große Kryptos in EUR)"
echo " - Agenten-Bot (Solana-Memecoins, alle 15 Sekunden)"
echo "Agenten-Log ansehen: journalctl -u jarvis-agents -f"
echo "Jarvis live: schreib deinem Telegram-Bot /status"
echo "Zugang später nochmal anzeigen: cat /root/jarvis-bot-zugang.txt"

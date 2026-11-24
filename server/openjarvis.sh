#!/usr/bin/env bash
# OpenJarvis (Stanford, Apache-2.0) – Nachfolger von Jarvis v1. Installiert + richtet alles ein.
# Auf dem netcup-Server als root ausführen:
#   curl -fsSL https://raw.githubusercontent.com/lucassebastianbehrens-lang/jarvis/main/server/openjarvis.sh | bash
# Die Hintergrund-Dienste von Jarvis v1 (Trading-Bot, Videos, Aufträge, Telegram) laufen unverändert weiter.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
[ "$(id -u)" = 0 ] || { echo "Bitte als root ausführen."; exit 1; }
U=openjarvis

echo ">> 1/5 Grundpakete"
apt-get update -qq && apt-get install -y -qq git curl zstd sudo >/dev/null

echo ">> 2/5 Eigener Benutzer '$U' (der Installer läuft nicht als root)"
id "$U" >/dev/null 2>&1 || useradd -m -s /bin/bash "$U"
echo "$U ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$U && chmod 440 /etc/sudoers.d/$U

echo ">> 3/5 OpenJarvis + Ollama + KI-Modell qwen3.5:2b (kostenlos, läuft auf dem Server, ca. 3–8 Min.)"
sudo -iu "$U" bash -c 'curl -fsSL https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/scripts/install/install.sh | bash -s -- --no-analytics'
# Server-Teil (für den Dauerbetrieb) nachinstallieren
sudo -iu "$U" bash -c 'export PATH=$HOME/.local/bin:$PATH; cd ~/.openjarvis/src && uv pip install -q --python ~/.openjarvis/.venv/bin/python -e ".[server]"'

echo ">> 4/5 Auf Lucas einrichten (Deutsch)"
H=/home/$U/.openjarvis
cat > $H/SOUL.md <<'EOF'
# Agent Persona

Du bist Jarvis, der persönliche KI-Assistent von Lucas.
- Antworte immer auf Deutsch, kurz und direkt.
- Beträge und Kurse immer in Euro.
- Was du selbst erledigen kannst, erledigst du und meldest danach kurz das Ergebnis.
- Bei Geld, Käufen, Löschen oder Veröffentlichen fragst du vorher kurz nach.
EOF
cat > $H/USER.md <<'EOF'
# User Profile

- Name: Lucas
- Wohnt in Halberstadt, zieht zum 01.01.2027 nach Oschersleben; arbeitet in Oschersleben im Schichtdienst
- Baut nebenbei eigene Online-Geschäfte auf (Shops, TikTok/YouTube-Content, Krypto-Trading-Bot im Spielgeld-Modus)
- Fährt einen BMW E46
EOF
chown $U:$U $H/SOUL.md $H/USER.md

echo ">> 5/5 Dauerbetrieb: Dienst startet automatisch (nur intern auf Port 8000)"
cat > /etc/systemd/system/openjarvis.service <<EOF
[Unit]
Description=OpenJarvis
After=network.target ollama.service
[Service]
User=$U
Environment=HOME=/home/$U
ExecStart=$H/.venv/bin/jarvis serve --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now openjarvis >/dev/null 2>&1 || true
# Kurzbefehl: 'jarvis' funktioniert auch direkt als root
cat > /usr/local/bin/jarvis <<EOF
#!/usr/bin/env bash
exec sudo -iu $U $H/.venv/bin/jarvis "\$@"
EOF
chmod +x /usr/local/bin/jarvis

echo
echo "✅ OpenJarvis ist fertig eingerichtet."
echo "   Chatten:  jarvis chat        Frage:  jarvis ask \"Wie spät ist es?\""
echo "   Prüfen:   jarvis doctor      Dienst: systemctl status openjarvis"
echo "   Telegram NICHT verbinden – den Bot nutzt gerade noch Jarvis v1/OpenClaw."

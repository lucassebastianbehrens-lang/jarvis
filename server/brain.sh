#!/usr/bin/env bash
# Jarvis-Gehirn: OpenClaw (selbst gehosteter KI-Agent, wie bei den TikTok-„Jarvis“-Videos) + 147 Agency-Agenten.
# Auf dem netcup-Server NACH server/setup.sh ausführen:
#   curl -fsSL https://raw.githubusercontent.com/lucassebastianbehrens-lang/jarvis/main/server/brain.sh | bash
set -euo pipefail
echo ">> 1/5 Node.js 24"
if ! node -v 2>/dev/null | grep -q '^v2[4-9]'; then
  curl -fsSL https://deb.nodesource.com/setup_24.x | bash - >/dev/null
  apt-get install -y -qq nodejs git >/dev/null
fi
echo ">> 2/5 OpenClaw installieren (offizieller Installer)"
command -v openclaw >/dev/null || curl -fsSL https://openclaw.ai/install.sh | bash
export PATH="$(npm prefix -g)/bin:$PATH"
echo ">> 3/5 Jarvis-Dateien holen"
rm -rf /opt/jarvis/repo && git clone -q --depth 1 https://github.com/lucassebastianbehrens-lang/jarvis.git /opt/jarvis/repo
echo ">> 4/5 Einrichtung – DU tippst die Schlüssel selbst ein:"
echo "   • KI-Anbieter: Google Gemini (kostenlos) ODER OpenRouter (kostenlose Modelle) – Schlüssel einfügen"
echo "   • Kanal: Telegram – Token deines Jarvis-Bots einfügen, NUR deine Telegram-ID erlauben"
echo "   • Skills: erstmal überspringen"
# Jarvis-live gibt Telegram an OpenClaw ab (ein Bot kann nur von einem Programm gelesen werden)
systemctl disable --now jarvis-live 2>/dev/null || true
openclaw onboard </dev/tty
echo ">> 5/5 147 Agency-Agenten (MIT-Lizenz) einbauen"
rm -rf /opt/agency-agents && git clone -q --depth 1 https://github.com/msitarzewski/agency-agents.git /opt/agency-agents
cd /opt/agency-agents && ./scripts/convert.sh --tool openclaw >/dev/null && ./scripts/install.sh --tool openclaw
openclaw gateway restart || true
echo
echo "✅ Fertig. Schreib deinem Telegram-Bot als erste Nachricht:"
echo "   „Lies /opt/jarvis/repo/brain/JARVIS.md und übernimm das dauerhaft als deine Identität, Regeln und Cron-Jobs.“"
echo "Status: openclaw gateway status"

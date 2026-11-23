#!/usr/bin/env bash
# OpenJarvis (Stanford, Apache-2.0) – Nachfolger von Jarvis v1.
# Auf dem netcup-Server als root ausführen:
#   curl -fsSL https://raw.githubusercontent.com/lucassebastianbehrens-lang/jarvis/main/openjarvis.sh | bash
# Die Hintergrund-Dienste von Jarvis v1 (Trading-Bot, Videos, Aufträge, Telegram) laufen unverändert weiter.
set -euo pipefail
echo ">> OpenJarvis installieren (offizieller Installer: uv, Python, Ollama, kleines Startmodell)"
curl -fsSL https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/scripts/install/install.sh | bash -s -- --no-analytics
echo
echo "✅ Fertig. Starten mit:  jarvis        (Status: jarvis doctor)"
echo "   Telegram NICHT verbinden – den Bot nutzt gerade noch OpenClaw/Jarvis v1."

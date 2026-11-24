#!/usr/bin/env bash
# Baut EIN fertig geprüftes Video für einen bestimmten Tag und legt es als Release
# „jarvis-video-<JJJJMMTT>-<modus>“ ab. Die täglichen Upload-Aufgaben (Simulation 17:30,
# Früchte-Serie 18:30) nehmen sich am jeweiligen Abend genau dieses Release.
#   bash bot/video_tag.sh <sim|tt|geld> <JJJJMMTT> [spec]
# Gibt es das Release für den Tag schon, passiert nichts (Exit 0). Exit 1 = Video durchgefallen.
set -uo pipefail
MODUS=$1; TAG_DATUM=$2; SPEC=${3:-}
TAG="jarvis-video-$TAG_DATUM-$MODUS"
if gh release view "$TAG" >/dev/null 2>&1; then echo "⏭  $TAG gibt es schon"; exit 0; fi

git pull -q --rebase origin main || true
if [ -z "$SPEC" ]; then
  SPEC=$(python3 bot/video_auto.py "$MODUS" | tail -n 1) || { echo "❌ Folge schreiben fehlgeschlagen"; exit 1; }
fi
ID=$(basename "$SPEC" .json)
echo "▶ $TAG_DATUM $MODUS: $ID"

OK=0
for RUNDE in 1 2 3; do
  echo "::group::$ID Runde $RUNDE/3"
  export SEED_SHIFT=$(( (RUNDE - 1) * 1000 ))
  rm -rf video/out/${ID}_tmp/i*.jpg video/out/${ID}_tmp/c*.mp4 video/out/$ID.mp4
  OK=1
  python3 video/$MODUS.py "$SPEC" || OK=0
  # Prüfung 1: Technik (Länge, Ton, kein schwarzes/eingefrorenes Bild)
  if [ $OK = 1 ]; then
    if [ "$MODUS" = sim ]; then python3 bot/video_check.py video/out/$ID.mp4 18 70 || OK=0
    else python3 bot/video_check.py video/out/$ID.mp4 40 120 || OK=0; fi
  fi
  # Prüfung 2: Bilder (nur Obst-/Gemüse-Figuren, nichts Anzügliches)
  if [ $OK = 1 ] && [ "$MODUS" != sim ]; then python3 bot/bild_check.py video/out/$ID.mp4 || OK=0; fi
  # Prüfung 3: Datei vollständig abspielbar
  if [ $OK = 1 ]; then ffmpeg -v error -i video/out/$ID.mp4 -f null - 2> /tmp/err.txt; [ -s /tmp/err.txt ] && { cat /tmp/err.txt; OK=0; }; fi
  echo "::endgroup::"
  [ $OK = 1 ] && { echo "✅ $ID: alle 3 Prüfungen bestanden (Runde $RUNDE)"; break; }
  echo "❌ $ID Runde $RUNDE durchgefallen – neuer Versuch"
done
[ $OK = 1 ] || exit 1

git add video/sim video/tt video/geld
git commit -qm "Jarvis: Folge $ID für $TAG_DATUM vorproduziert" || true
for i in 1 2 3 4; do git pull -q --rebase origin main && git push -q origin HEAD:main && break; sleep 5; done
F=(); for e in mp4 jpg txt; do [ -f "video/out/$ID.$e" ] && F+=("video/out/$ID.$e"); done
TAG_ANZEIGE="${TAG_DATUM:6:2}.${TAG_DATUM:4:2}.${TAG_DATUM:0:4}"
gh release create "$TAG" "${F[@]}" --title "Jarvis-Video $MODUS für $TAG_ANZEIGE" \
  --notes "Vorproduziert und 3-fach geprüft: $ID – wird am $TAG_ANZEIGE abends hochgeladen."
echo "$TAG_ANZEIGE $ID" >> video/out/fertig.txt

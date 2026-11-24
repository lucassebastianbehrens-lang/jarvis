"""Serie „Kontostand“: gleicher Renderer wie die Früchte-Serie (tt.py) – plus LED-Kontostand-Anzeigen aus dem Feld „konto“.
Aufruf: python3 video/geld.py video/geld/<id>.json   Ausgabe: video/out/<id>.mp4 + <id>.txt"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from tt import build

if __name__ == "__main__":
    bad = []
    for f in sys.argv[1:]:
        try:
            build(f)
        except Exception:
            import traceback; traceback.print_exc(); bad.append(f)
    sys.exit(1 if bad else 0)

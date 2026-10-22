#!/usr/bin/env python3
"""Packt ein Deck (project/deck.json + project/slides/*.html) und den Viewer
in eine einzelne HTML-Datei, die sich auch per file:// öffnen lässt.

    python3 build_standalone.py <deck-ordner> <ausgabe.html> [--tokens tokens.json]

<deck-ordner> ist der Ordner, der `project/` enthält. Lokale Bilder und
Schriften unter project/ werden als data:-URI eingebettet. Verweise der Form
/_blob/<id> gehören der Artifact-Plattform und bleiben unaufgelöst.
"""
import argparse, base64, json, mimetypes, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = re.compile(r'''(src|url)(=|\()(["']?)(project/[^"')\s]+)\3''')


def inline(text: str, root: Path) -> str:
    def sub(m):
        rel = m.group(4)
        f = (root / rel).resolve()
        if root.resolve() not in f.parents or not f.is_file():
            return m.group(0)
        mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        data = base64.b64encode(f.read_bytes()).decode()
        return f'{m.group(1)}{m.group(2)}{m.group(3)}data:{mime};base64,{data}{m.group(3)}'
    return LOCAL.sub(sub, text)


def js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("deck_root", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--tokens", type=Path, default=HERE / "tokens.json")
    a = ap.parse_args()

    proj = a.deck_root / "project"
    deck = json.loads((proj / "deck.json").read_text(encoding="utf-8"))
    slides = {}
    for sid in deck.get("order", []):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", sid):
            sys.exit(f"Ungültige Folien-ID: {sid!r}")
        f = proj / "slides" / f"{sid}.html"
        if not f.is_file():
            sys.exit(f"Folie fehlt: {f}")
        slides[sid] = inline(f.read_text(encoding="utf-8"), a.deck_root)
    tokens = json.loads(a.tokens.read_text(encoding="utf-8"))

    tpl = (HERE / "viewer.html").read_text(encoding="utf-8")
    payload = f"<script>window.__DECK__={js({'deck': deck, 'slides': slides})};window.__TOKENS__={js(tokens)};</script>"
    if "<!--INJECT-->" not in tpl:
        sys.exit("Platzhalter <!--INJECT--> fehlt im Viewer.")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(tpl.replace("<!--INJECT-->", payload), encoding="utf-8")
    print(f"{len(slides)} Folien -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Rebuild the template deck from examples/: after changing the palette in theme.css (or an
example), so the example slides show the new style. REPLACES EVERY SLIDE of the deck, so it runs
only in a folder whose name contains `template` (`--force` to override).

    python tools/build_examples.py .        # from inside the template

Re-stages the animation page (examples/web/steps.html) with `slide-agent web add` and points
the animation example at it; the 3D page in assets/web/ is kept as is (it uses no theme colour).
Then numbers the pages. Needs what tools/number_slides.py needs.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from number_slides import SLIDE_AGENT

EMPTY_DECK = {"version": 1, "title": "Slide template", "canvas": {"w": 1920, "h": 1080},
              "theme": "theme.css", "slides": [{"id": "slide-1", "name": "Slide 1"}]}
STEPS = "examples/web/steps.html"


def agent(*args):
    out = subprocess.run([SLIDE_AGENT, *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out[out.index("{"):])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("deck", type=Path)
    ap.add_argument("--force", action="store_true", help="run in a folder not named *template*")
    args = ap.parse_args()
    deck = args.deck.resolve()
    if "template" not in deck.name and not args.force:
        sys.exit(f"{deck} is not the template: this replaces every slide (pass --force to do it anyway)")

    for scratch in ("edit", "drafts", ".versions"):
        shutil.rmtree(deck / scratch, ignore_errors=True)
    for scratch in ("history.jsonl", "notes.md"):
        (deck / scratch).unlink(missing_ok=True)
    (deck / "deck.json").write_text(json.dumps(EMPTY_DECK))
    (deck / "drafts").mkdir()

    staged = agent("web", "add", str(deck), str(deck / STEPS), "--size", "1728x600",
                   "--title", "Three steps, one per click")
    stem = Path(staged["src"]).name.split(".")[0]
    for old in (deck / "assets/web").glob(f"{stem}.*"):   # earlier stagings of the same page
        if f"assets/web/{old.name}" not in (staged["src"], staged["poster"]):
            old.unlink()

    for i, example in enumerate(sorted((deck / "examples").glob("0*.html"))):
        page = example.read_text()
        page = re.sub(rf"assets/web/{stem}\.[0-9a-f]+\.html", staged["src"], page)
        page = re.sub(rf"assets/web/{stem}\.[0-9a-f]+\.poster\.png", staged["poster"], page)
        example.write_text(page)
        if i == 0:   # replaces the empty deck's one slide
            page = page.replace('<section class="slide', '<section data-slide-id="slide-1" class="slide', 1)
        draft = deck / "drafts" / example.name
        draft.write_text(page)
        changes = agent("apply", str(deck), "--html", str(draft)).get("changes", {})
        if changes.get("deleted"):
            sys.exit(f"{example.name}: unexpected deletions {changes['deleted']}")
        print(example.name, {k: v for k, v in changes.items() if v not in ([], 0)})

    subprocess.run([sys.executable, str(Path(__file__).with_name("number_slides.py")), str(deck)],
                   check=True)


if __name__ == "__main__":
    main()

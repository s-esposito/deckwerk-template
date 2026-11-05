#!/usr/bin/env python3
"""Page numbers for a DeckWerk deck, which has no slide-number field: every slide but the first
(title) and the last (closing) gets its position, in a page-number box (bottom right, in the
theme's --muted colour and --sans font), replacing whatever number box it had (any bottom-right text box holding
only a number). Run after adding, deleting or moving slides.

    python tools/number_slides.py .        # from inside the deck folder

Goes through DeckWerk's own authoring round trip: `slide-agent inspect --html --all` into the
deck's edit/, then `slide-agent apply`. Needs `slide-agent` (bin/ of a DeckWerk checkout) on PATH
or in $SLIDE_AGENT, Node >= 22 on PATH, and `pip install beautifulsoup4`.
"""
import argparse
import json
from html import escape as html_escape
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

SLIDE_AGENT = os.environ.get("SLIDE_AGENT") or shutil.which("slide-agent") or "slide-agent"
#: The page-number box, ``{n}`` the page, ``{color}``/``{font}`` the theme's ``--muted``/``--sans``.
BOX = ('<div class="element element-text pp-text role-body" data-valign="top" '
       'data-paragraph-spacing="5.3" style="position:absolute; left:1747.2px; top:998.4px; '
       'width:115.2px; height:48px; font-size:27px; font-family:{font}; font-weight:400; color:{color}; '
       'padding:9.6px 19.2px 9.6px 19.2px; text-align:left; --paragraph-spacing:5.3px;">'
       '<div class="text-body" data-element="none" style="display:flex; flex-direction:column; '
       'justify-content:flex-start; width:100%; height:100%;"><div class="text-content" '
       'data-text-content style="width:100%; color:{color}; font-family:{font}; font-weight:400;">'
       '<ul><li>{n}</li></ul></div></div></div>')
NUMBER = re.compile(r"^[\s •·]*\d+$")


def _px(style, key):
    m = re.search(rf"(?:^|;)\s*{key}:\s*([\d.]+)px", style or "")
    return float(m[1]) if m else -1.0


def number_boxes(section):
    """The section's page-number boxes: bottom-right text elements holding only a number."""
    return [e for e in section.select("[data-element-id].element-text")
            if NUMBER.match(e.get_text()) and _px(e.get("style"), "left") >= 1500
            and _px(e.get("style"), "top") >= 900]


def theme_style(deck):
    """The deck's ``--muted`` colour and ``--sans`` font (from its theme.css), HTML-escaped."""
    css = (deck / "theme.css").read_text()
    var = lambda name, default: (re.search(rf"--{name}:\s*([^;]+);", css) or [None, default])[1].strip()
    return {"color": var("muted", "#8aa1ae"),
            "font": html_escape(var("sans", "Calibri, Carlito, sans-serif"), quote=True)}


def renumber(html, style):
    """``html`` (an ``inspect --html --all`` page) with every page-number box set in ``style``;
    the number of boxes changed."""
    soup = BeautifulSoup(html, "html.parser")
    sections = soup.select("section.slide")
    changed = 0
    for i, section in enumerate(sections, start=1):
        if i in (1, len(sections)):
            continue
        boxes = number_boxes(section)
        if (len(boxes) == 1 and boxes[0].ul and boxes[0].get_text().strip() == str(i)
                and abs(_px(boxes[0].get("style"), "width") - 115.2) < 0.1   # DeckWerk rounds
                and not boxes[0].get("data-autofit")):
            continue   # already this box with the right number
        box = BeautifulSoup(BOX.format(n=i, **style), "html.parser").div
        if boxes:
            box["data-element-id"] = boxes[0]["data-element-id"]
            if boxes[0].get("data-base"):
                box["data-base"] = boxes[0]["data-base"]
            boxes[0].replace_with(box)
            for extra in boxes[1:]:
                extra.decompose()
        else:
            section.append(box)
        changed += 1
    return str(soup), changed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("deck", type=Path)
    args = ap.parse_args()
    env = os.environ
    page = args.deck / "edit" / "page_numbers.html"
    page.parent.mkdir(exist_ok=True)
    html = subprocess.run([str(SLIDE_AGENT), "inspect", str(args.deck), "--html", "--all"], env=env,
                          check=True, capture_output=True, text=True).stdout
    html, changed = renumber(html, theme_style(args.deck))
    if not changed:
        print("page numbers already right")
        return
    page.write_text(html)
    out = subprocess.run([str(SLIDE_AGENT), "apply", str(args.deck), "--html", str(page),
                          "--label", "page numbers"], env=env, check=True, capture_output=True, text=True)
    changes = json.loads(out.stdout[out.stdout.index("{"):]).get("changes", {})
    print(f"{changed} page number(s) set; deck changes:",
          {k: v for k, v in changes.items() if v not in ([], 0)})
    if changes.get("deleted") or changes.get("inserted"):
        sys.exit("unexpected slide deletions/insertions: check the deck")


if __name__ == "__main__":
    main()

# DeckWerk progress-report template

A DeckWerk deck (https://github.com/vsitzmann/deckwerk) for progress reports, with seven example
slides: title, last week, a qualitative image grid, a quantitative chart + table, a web animation
stepped by clicks, a live 3D viewer, and next steps. These rules are for people and their coding
agents alike. DeckWerk generates an `AGENTS.md` in every deck it opens; this one has no
"generated" marker, so it is kept as is.

Tools: `slide-agent` (`bin/` of a DeckWerk checkout, after `npm install`) on PATH or in
`$SLIDE_AGENT`; Node >= 22 on PATH; Python 3 with `beautifulsoup4` for `tools/`.

## Your style

Every colour and font comes from the block at the top of `theme.css`. To make the template
yours: edit that block (and the matching `:root` block of `examples/web/steps.html`), then rebuild
the example deck with `python tools/build_examples.py .`, and copy your decks from there.
`slide-agent apply` bakes the values into each slide, so a palette change restyles the slides
written afterwards, never those already in a deck.

## Start a new deck

    cp -r deckwerk-template <dd-mm-yyyy> && rm -rf <dd-mm-yyyy>/.git     # one folder per report
    cd <dd-mm-yyyy>

Then rewrite the title, "Last week" and "Next" slides, add your content slides (below), and
delete the example content slides (and their `assets/placeholder_*`, `assets/web/steps.*`,
`assets/web/example_3d.*`) once yours are in.

## Files

| Path | What it is |
|------|-----------|
| `deck.json` | The deck. **Never read or edit it**; DeckWerk owns it |
| `theme.css` | Palette and fonts (top block), then the layout classes below |
| `examples/0*.html` | Source pages of the example slides, in deck order. Copy one to start a slide; never apply them directly |
| `examples/web/steps.html` | Source page of the web animation |
| `assets/` | Images and models the slides use, referred to as `assets/<name>`; `assets/web/` holds staged web pages |
| `tools/number_slides.py` | Writes the page numbers |
| `tools/build_examples.py` | Rebuilds this template's example deck (replaces every slide; runs only in the template) |
| `tools/build_deck_3d_viewer.py` | Packs a 3D model into one offline viewer page |
| `drafts/`, `edit/`, `.versions/`, `history.jsonl` | Scratch (yours and DeckWerk's), not committed |

## Workflow

1. **Look at the neighbours**: `slide-agent render . --slide 3,4 --output /tmp/ctx` (PNGs) and
   `slide-agent inspect . --html-body --slide 3,4` (their markup). Slides are numbered as in the
   editor's rail.
2. **Write the slide** as `drafts/<name>.html`, starting from a copy of the closest
   `examples/0*.html`. It is an ordinary 1920x1080 web page (`<base href="../">`, links
   `theme.css`); preview it in any browser.
3. **Apply it**: `slide-agent apply . --html drafts/<name>.html --after <n>` (or without `--after`
   to append). The first apply stamps a `data-slide-id` into the file, and applying that file
   again *replaces* the slide: start every *new* slide from a fresh copy. To replace an existing
   slide, put its id (from `inspect --html-body`) on your `<section>`. Read `changes` in the
   output: an unintended `deleted` means stop and undo in the editor.
4. **Check it**: `slide-agent render . --slide <n> --output /tmp/final`, compared with the browser.
   `slide-agent validate .` lists overflows.
5. **Delete or reorder slides**: `mkdir -p edit && slide-agent inspect . --html --slide 3,4 >
   edit/work.html`, remove or reorder the `<section>`s there, then `slide-agent apply . --html
   edit/work.html` (a section removed from that page deletes its slide).
6. **Number the pages** after adding, deleting or moving slides: `python tools/number_slides.py .`
   (every slide but the first and the last; never write a page number by hand).

## Layout

Every content slide has the same frame (px, canvas 1920x1080, 96 px side margins):

| Part | Class | Where | What goes in it |
|------|-------|-------|-----------------|
| Title | `.s-title` | y 58-202, centred | The slide's one result as a statement ("B halves the time at the same quality"), not a topic ("Timing") |
| Setup | `.s-setup` | y 192-268, centred | What was run, on which data, seen from where; how many runs a number averages |
| Body | (see below) | y 270-870 | The evidence |
| Takeaway | `.s-takeaway` | y 880-995 | One italic sentence the evidence supports |
| Page number | (tool) | bottom right | Written by `tools/number_slides.py` |

The cover slides (first and last) use `<section class="slide s-cover">` with `.s-cover-title`
and `.s-cover-sub` (title: `Weekly progress · dd-mm-yyyy`) or `.s-cover-list` (next steps).

Body pieces, each positioned with inline `left/top/width/height`:
- `.s-col` column header, `.s-row` row label (right-aligned, centred on its row), `.s-img` image;
- `.s-legend` + `.s-swatch` colour legend, `.s-note` small print (a metric under an image, what
  a metric measures);
- `.s-bar` horizontal bar (`width` = value x a scale shared by all bars, value printed inside),
  coloured `var(--c1)`..`var(--c4)` in that order;
- `.s-table` table with rules under rows only, the best value per column in `.s-best`;
- `.s-text` bullets or prose;
- a web element (below) for anything that needs JavaScript.

Text sizes: title 80, takeaway 40, bullets 36, setup 30, labels 26-28, small print 20-22; nothing
below 18. Colours only through the palette variables (`var(--ink)`, ...), never a hex code in a
slide, so a palette change reaches every slide.

## Web elements: animations and live 3D

A web element is a self-contained HTML page shown live in its box (sandboxed: scripts run, no
network, so inline everything). Keep the title, setup and takeaway as ordinary slide text
outside the box. Stage a page with `slide-agent web add . page.html --size 1728x600 --title "..."`:
it copies the page to `assets/web/<name>.<hash>.html`, captures a poster, and prints the
`<div data-element="web" ...>` to place in your slide (give it `position:absolute; left; top`).
After editing the page, `web add` it again and update `data-src`/`data-poster`, or
`slide-agent web replace . <slide> page.html`. More: `slide-agent docs web`.

- **Animation stepped by clicks** (slide 5, `examples/web/steps.html`): the page listens to
  `deckwerk.onStep(({ step }) => ...)` and `deckwerk.onActive(({ step }) => ...)`; the slide holds
  one invisible `<div data-build="click">` marker per click (2 markers = steps 0-2). On
  `onActive` jump straight to the settled state of that step (the slide may open at its last
  step, and PDF export captures each step that way).
- **Live 3D viewer** (slide 6): `tools/build_deck_3d_viewer.py` packs 3DView
  (https://github.com/s-esposito/3DView) and a PLY/GLB (splats, mesh or point cloud) into one page:

      curl -L -o webview.js https://s-esposito.github.io/3DView/dist/webview.js
      python tools/build_deck_3d_viewer.py webview.js drafts/<name>_3d.html \
          --still still.png --label "<scene>" <model>.glb
      slide-agent web add . drafts/<name>_3d.html --size 1728x600 --title "<scene> in 3D"

  `--still` is shown until the scene has loaded (a screenshot of the loaded viewer, e.g. from
  `slide-agent web check drafts/<name>_3d.html --size 1728x600 --screenshot still.png`). Pages
  are ~5 MB plus the model, so **name them `*_3d.html`**: `.gitignore` keeps `assets/web/*_3d.*`
  out of git (only the template's own example is committed).

## Content rules

- **One message per slide, and as few slides as the message needs.** Cut every number, caveat and
  step that does not support that slide's message.
- **Lead with the result or decision.** How you got there (dead ends, tooling, intermediate
  diagnostics) stays out unless it changes a decision.
- **Evidence for every claim:** a qualitative comparison (images) always, a quantitative one
  (chart or table) wherever there are numbers.
- **An error map beside every render of a real camera**: each render compared against a real
  image gets its |render - image| map right next to it (white = no error, darker = larger), with
  the colour scale in the legend.
- **Plain words.** Say what each picture shows (which view, what the rows, columns and colours
  mean) and what each number measures, with its unit and direction (higher/lower is better). No
  internal shorthand: a reader who missed the work must follow the slide alone.
- **Name the exact variant in every result label** (method + configuration/backbone, e.g.
  "ours + backbone X"), in titles, labels and captions alike; the bare method name only for the
  method itself.
- **Numbers carry their spread**: when a result is noisy, report the mean of several runs and the
  spread (± or min-max), and say how many runs in the setup line.
- **Same scale, same view**: images compared side by side share size, crop and viewpoint; bars
  compared share one axis.
- **Slide 2 is "Last week"**: the previous report in one slide, one bullet per topic
  (`<b>Topic:</b>` + its result in one sentence), plus the takeaway this week starts from.
- **The last slide is "Next"**: the next steps, filled at the end of the week.
- **When in doubt about granularity** (what goes in, what stays out, how much detail), agents ask
  the presenter before building.

## DeckWerk pitfalls

- `apply` bakes each element's computed style into the slide, and classes are not kept: editing
  `theme.css` changes the slides you write afterwards, not those already in the deck.
- Every image is its own element: an `<img>` inside a text element (e.g. a colour bar inside a
  legend line) splits the text apart. Place the bar as its own `.s-img` between two labels.
- A table loses its class in the deck and the player draws a 1px cell grid; the reset in
  `theme.css` (`.slide .text-body :is(th, td)`) removes it, so keep it when changing the theme.
- Nothing in a web page may sit over it and catch the pointer: while presenting, clicks must reach
  the page from the start (the 3D builder's still image lets them through).
- More: `slide-agent docs authoring`.

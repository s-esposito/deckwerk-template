"""One self-contained HTML page showing 3D assets (splat / mesh / cloud PLY or GLB) in 3DView, for
a DeckWerk web element (`slide-agent web add|replace`).

3DView (https://github.com/s-esposito/3DView, three.js + Spark) is the viewer of the GenIA
project page; its host logic here follows that page's viewer3d.html. A web element runs in a
`sandbox="allow-scripts"` frame with no network, so everything is inlined: the viewer bundle and
the assets (base64, handed to the viewer as Blob URLs). Two sandbox fixes:

* Spark's sort worker is a MODULE worker from a blob: URL that imports the core module from
  another blob: URL, which Chrome refuses in an opaque origin. It is rebuilt from a data: URL
  of that core module (`sandbox_safe_workers`; the minified names are read from the bundle and
  anything unexpected raises).
* The viewer's display defaults (box / grid / axes / points off) are toggled with synthetic key
  presses; DeckWerk forwards unhandled presenting keys to the deck, where 'b' blacks out the
  screen, so they are marked handled before its bridge sees them.

The viewer starts on load; `--still` (the slide's poster, e.g. a screenshot of the loaded
viewer) stays on top until the scene has finished decoding or the viewer is first pressed. It
never takes input: a still that caught clicks left the viewer dead for the seconds a large
scene takes to decode, which while presenting read as "click a few times until it reacts".

    curl -L -o webview.js https://s-esposito.github.io/3DView/dist/webview.js
    python tools/build_deck_3d_viewer.py webview.js drafts/<name>_3d.html \\
        --still still.png --label "<scene>" <model>.ply|.glb
    slide-agent web add . drafts/<name>_3d.html --size 1728x600 --title "<scene> in 3D"

Sizes: the bundle is ~4.6 MB, assets grow by a third (base64); keep a page to tens of MB.
"""
import argparse
import base64
import json
import os
import re


def sandbox_safe_workers(js: str) -> str:
    core = re.findall(r'static get coreUrl\(\)\{return (\w+)\?\?\(\1=\w+\((\w+)\)\)\}', js)
    serve = re.findall(r'(\w+) as serveWorker\}', js)
    spawn = re.findall(r'new Worker\(\w+\?\?\(\w+=\w+\(`import \{ serveWorker \} from \$\{JSON\.stringify'
                       r'\(\w+\.coreUrl\)\}; serveWorker\(\);`\)\),\{type:"module"\}\)', js)
    assert len(core) == 1 and len(set(serve)) == 1 and len(spawn) == 1, \
        f"3DView bundle layout changed: coreUrl {core}, serveWorker {set(serve)}, spawns {len(spawn)}"
    return js.replace(spawn[0], f'new Worker("data:text/javascript;charset=utf-8,"'
                                f'+encodeURIComponent({core[0][1]}+"\\n{serve[0]}();"),{{type:"module"}})')


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; background: #fff;
    font-family: Calibri, Carlito, sans-serif; }
  canvas { display: block; position: fixed; top: 0; left: 0; }
  #still { position: fixed; inset: 0; width: 100%; height: 100%; object-fit: contain; z-index: 50;
    pointer-events: none; }   /* input reaches the viewer from the start */
  #status { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); padding: 10px 16px;
    color: #e6e6e6; background: rgba(20, 20, 22, .72); border-radius: 10px; font-size: 16px;
    z-index: 100; pointer-events: none; }
  #viewer-ui > .viewer-panel:first-child { display: none; }
  html body[data-viewer-theme="light"] { --vscode-editor-background: #fff; }
</style></head><body>
<img id="still" alt="" src="@STILL@">
<div id="status">Loading 3D view…</div>
<script type="text/plain" id="assets">@DATA@</script>
<script>
(function () {
  var LABEL = @LABEL@;
  function blobUrl(b64) {
    var bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return URL.createObjectURL(new Blob([bytes], { type: 'application/octet-stream' }));
  }
  function assetMessage() {
    var data = JSON.parse(document.getElementById('assets').textContent);
    var items = Object.keys(data).map(function (name, i) {
      return { type: 'addAsset', id: 'asset-' + i, label: name, asset: { uri: blobUrl(data[name]), name: name } };
    });
    if (items.length === 1) { items[0].label = LABEL; return items[0]; }
    return { type: 'addGroup', id: 'group-0', label: LABEL, members: items, grouping: 'separate' };
  }
  // Synthetic key presses are ours: handled here, so DeckWerk's bridge does not forward them
  // ('b' blacks out a presentation); the viewer's own listener ignores defaultPrevented.
  window.addEventListener('keydown', function (e) { if (!e.isTrusted) e.preventDefault(); }, true);
  // As the project page: light theme, box / grid / axes / points off.
  function presentationDefaults() {
    var light = document.querySelector('#viewer-ui .viewer-seg-opt[aria-label="Light"]');
    if (light) light.click();
    ['b', 'g', 'a', 'p'].forEach(function (key) {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: key, bubbles: true, cancelable: true }));
    });
  }
  // The still never takes input (the viewer gets every click and drag from the start), and the
  // first press on the viewer takes it off, so the audience sees what is being turned.
  window.addEventListener('pointerdown', function () {
    var still = document.getElementById('still');
    if (still) still.remove();
  }, true);
  // The still comes off once the scene is in: 3DView shows a spinner while decoding and hides
  // its status line when the scene has content (90 s at most).
  function revealWhenLoaded() {
    var status = document.getElementById('status'), spun = false, t0 = Date.now();
    var timer = setInterval(function () {
      if (status.querySelector('.viewer-spinner')) spun = true;
      if ((spun && getComputedStyle(status).display === 'none') || Date.now() - t0 > 90000) {
        clearInterval(timer);
        var still = document.getElementById('still');
        if (still) still.remove();
      }
    }, 200);
  }
  // Read by the bundle at startup, so it must exist before the bundle's script runs.
  window.__viewerHost = {
    postMessage: function (msg) {
      if (msg.type !== 'ready') return;
      presentationDefaults();
      window.postMessage(assetMessage(), '*');
      revealWhenLoaded();
    }
  };
})();
</script>
<script>@JS@</script>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("bundle", help="3DView's dist/webview.js")
    ap.add_argument("out", help="the page to write")
    ap.add_argument("assets", nargs="+", help="PLY / GLB files, shown as one scene")
    ap.add_argument("--still", required=True, help="PNG shown until the scene has loaded")
    ap.add_argument("--label", default="scene", help="the scene's name in the viewer's panel")
    args = ap.parse_args()

    js = open(args.bundle, encoding="utf-8").read()
    assert "</script" not in js.lower()
    b64 = lambda path: base64.b64encode(open(path, "rb").read()).decode()
    data = {os.path.basename(a): b64(a) for a in args.assets}
    page = (PAGE.replace("@STILL@", "data:image/png;base64," + b64(args.still))
            .replace("@LABEL@", json.dumps(args.label))
            .replace("@DATA@", json.dumps(data))
            .replace("@JS@", sandbox_safe_workers(js)))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"{args.out}: {os.path.getsize(args.out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

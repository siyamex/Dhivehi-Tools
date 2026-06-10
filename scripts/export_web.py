"""Build a fully client-side spell-checker bundle in dist/web/.

Usage:  python scripts/export_web.py

Produces three static files — host them anywhere (e.g. radheef.siyamex.com)
or open index.html straight from disk; everything runs in the browser:

  dist/web/index.html    standalone UI (spell check + Latin-input IME)
  dist/web/dhivehi.js    the client-side engine (copied from web_static)
  dist/web/lexicon.js    the full lexicon as a JS string
"""

from __future__ import annotations

import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhivehi_spell.checker import SpellChecker  # noqa: E402

HERE = os.path.dirname(__file__)
STATIC = os.path.join(HERE, "..", "dhivehi_tools", "web_static")
OUT = os.path.join(HERE, "..", "dist", "web")

PAGE = """<!DOCTYPE html>
<html lang="dv" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dhivehi Spell Checker — offline</title>
<style>
  @font-face { font-family:"MV Typer";
               src:url("fonts/mvtyper.ttf") format("truetype");
               font-display:swap; }
  body { margin:0; background:#f6f7f9; color:#1c2430;
         font-family:"Segoe UI",system-ui,sans-serif; }
  header { padding:14px 22px; background:#fff; border-bottom:1px solid #dde2ea;
           display:flex; gap:14px; align-items:baseline; flex-wrap:wrap; }
  h1 { font-size:18px; margin:0; }
  main { max-width:900px; margin:0 auto; padding:18px 22px; }
  textarea { width:100%; height:300px; font-size:24px; line-height:2.1;
             direction:rtl; padding:16px 18px; border:1px solid #dde2ea;
             border-radius:10px; box-sizing:border-box; outline:none;
             font-family:"MV Typer","MV Boli","Faruma","Noto Sans Thaana",sans-serif; }
  #issues { margin-top:14px; display:flex; flex-direction:column; gap:8px; }
  .card { background:#fff; border:1px solid #dde2ea; border-radius:10px;
          padding:10px 12px;
          font-family:"MV Typer","MV Boli","Faruma","Noto Sans Thaana",sans-serif; }
  .badge { font-size:11px; color:#fff; border-radius:10px; padding:2px 8px;
           margin-inline-start:8px; font-family:"Segoe UI",sans-serif; }
  .structure { background:#e53935; } .unknown { background:#fb8c00; }
  .chip { display:inline-block; margin:4px 3px 0 3px; padding:3px 12px;
          background:#eef3fb; color:#1565c0; border-radius:14px;
          cursor:pointer; font-size:18px; }
  .muted { color:#67738a; font-size:13px; }
</style>
</head>
<body>
<header>
  <h1>Dhivehi Spell Checker</h1>
  <span class="muted">runs entirely in your browser — no server</span>
  <label class="muted" style="margin-inline-start:auto">
    <input type="checkbox" id="ime"> Latin typing</label>
  <span class="muted" id="stat">loading lexicon…</span>
</header>
<main>
  <textarea id="ed" spellcheck="false" lang="dv"
    placeholder="މިތާ ދިވެހި ބަހުން ލިޔުއްވާ..."></textarea>
  <div id="issues"></div>
</main>
<script src="dhivehi.js"></script>
<script src="lexicon.js"></script>
<script>
"use strict";
var spell = new DV.Spell();
setTimeout(function () {
  spell.load(window.DV_LEXICON);
  document.getElementById("stat").textContent =
    spell.words.size.toLocaleString() + " words loaded";
  check();
}, 30);
var ed = document.getElementById("ed"), timer = null;
DV.attachIME(ed, function () { return document.getElementById("ime").checked; });
ed.addEventListener("input", function () {
  clearTimeout(timer); timer = setTimeout(check, 350);
});
function esc(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;"); }
function check() {
  if (!spell.words.size) return;
  var box = document.getElementById("issues");
  box.innerHTML = "";
  var re = /[\\u0780-\\u07B1]+/g, m;
  while ((m = re.exec(ed.value)) !== null) {
    var r = spell.check(m[0]);
    if (r.status === "ok") continue;
    var div = document.createElement("div");
    div.className = "card";
    var html = "<span style='font-size:21px'>" + esc(m[0]) + "</span>" +
               "<span class='badge " + r.status + "'>" + r.status + "</span><div>";
    (r.suggestions || []).forEach(function (s) {
      html += "<span class='chip' data-w='" + esc(s.word) +
              "' data-a='" + m.index + "' data-b='" + (m.index + m[0].length) +
              "'>" + esc(s.word) + "</span>";
    });
    div.innerHTML = html + "</div>";
    box.appendChild(div);
  }
  if (!box.children.length)
    box.innerHTML = "<div class='card muted'>No spelling issues found ✓</div>";
}
document.getElementById("issues").addEventListener("click", function (ev) {
  var t = ev.target;
  if (!t.classList.contains("chip")) return;
  var a = +t.dataset.a, b = +t.dataset.b;
  ed.value = ed.value.slice(0, a) + t.dataset.w + ed.value.slice(b);
  check();
});
</script>
</body>
</html>
"""


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    lexicon = SpellChecker().lexicon

    lex_path = os.path.join(OUT, "lexicon.js")
    with open(lex_path, "w", encoding="utf-8") as fh:
        fh.write('window.DV_LEXICON = "')
        chunks = []
        for word in lexicon.iter_words():
            chunks.append("%s\\t%d" % (word, lexicon.frequency(word)))
        fh.write("\\n".join(chunks))
        fh.write('";\n')

    shutil.copy(os.path.join(STATIC, "dhivehi.js"),
                os.path.join(OUT, "dhivehi.js"))
    font_src = os.path.join(STATIC, "fonts", "mvtyper.ttf")
    if os.path.exists(font_src):
        os.makedirs(os.path.join(OUT, "fonts"), exist_ok=True)
        shutil.copy(font_src, os.path.join(OUT, "fonts", "mvtyper.ttf"))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(PAGE)

    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _dirs, files in os.walk(OUT) for f in files)
    print("wrote %s (%d words, %.1f MB total)"
          % (os.path.normpath(OUT), len(lexicon), size / 1e6))


if __name__ == "__main__":
    main()

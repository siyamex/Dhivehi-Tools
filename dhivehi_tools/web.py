"""Unified local web server for all Dhivehi Tools.

  GET  /                   tabbed UI (spelling/grammar/paraphrase/dictionary/convert)
  GET  /api/stats          {"words", "synonyms", "definitions"}
  GET  /api/unknowns       unknown words users have typed, with counts
  POST /api/spell/check    {"text"} -> {"issues": [...]}
  POST /api/spell/add      {"words": [...]}
  POST /api/grammar/check  {"text"} -> {"issues": [...]}
  POST /api/paraphrase     {"text", "aggressiveness"?, "seed"?, "modern_only"?}
  POST /api/define         {"q"} -> dictionary lookup (exact + prefix)
  POST /api/translit       {"text", "to": "thaana"|"latin"}
  POST /api/register       {"text", "target": "formal"|"informal"}
  POST /v2/check           LanguageTool-compatible API (form-encoded)

Pure stdlib, binds to localhost, fully offline.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.parse
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional

from dhivehi_spell.checker import SpellChecker

from .grammar import GrammarChecker
from .paraphrase import Paraphraser
from .transform import to_formal, to_informal
from .translit import latin_to_thaana, thaana_to_latin

STATIC_DIR = os.path.join(os.path.dirname(__file__), "web_static")
DEFINITIONS_PATH = os.path.join(os.path.dirname(__file__), "data",
                                "definitions.tsv")


def _load_definitions(path: str) -> Dict[str, List[str]]:
    defs: Dict[str, List[str]] = defaultdict(list)
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t", 1)
                if len(parts) == 2:
                    defs[parts[0]].append(parts[1])
    return dict(defs)


class Tools:
    """Lazily-built shared tool instances."""

    def __init__(self, user_wordlist: Optional[str] = None) -> None:
        extra = ([user_wordlist]
                 if user_wordlist and os.path.exists(user_wordlist) else [])
        self.spell = SpellChecker(extra_wordlists=extra)
        self.grammar = GrammarChecker()
        self.paraphraser = Paraphraser()
        self.definitions = _load_definitions(DEFINITIONS_PATH)
        self.sorted_headwords = sorted(self.definitions)
        # inverted index over definition text, for reverse lookup
        self.def_index: Dict[str, set] = defaultdict(set)
        from dhivehi_spell.thaana import tokenize as _tok
        for head, senses in self.definitions.items():
            for sense in senses:
                for t in _tok(sense):
                    if len(t.word) >= 2:
                        self.def_index[t.word].add(head)
        self.unknown_log: Counter = Counter()
        self.user_wordlist = user_wordlist
        self.lock = threading.Lock()

    def log_unknowns(self, issues: List[Dict]) -> None:
        for issue in issues:
            if issue.get("status") == "unknown":
                self.unknown_log[issue["word"]] += 1

    def define(self, query: str, limit: int = 30) -> Dict:
        exact = self.definitions.get(query, [])
        prefix = []
        if query:
            import bisect
            i = bisect.bisect_left(self.sorted_headwords, query)
            while (i < len(self.sorted_headwords)
                   and len(prefix) < limit
                   and self.sorted_headwords[i].startswith(query)):
                w = self.sorted_headwords[i]
                if w != query:
                    prefix.append({"word": w,
                                   "definition": self.definitions[w][0]})
                i += 1
        return {"word": query, "definitions": exact, "related": prefix}

    def reverse_lookup(self, query: str, limit: int = 50) -> Dict:
        """Find headwords whose *definition* contains every query word."""
        from dhivehi_spell.thaana import tokenize as _tok
        terms = [t.word for t in _tok(query) if len(t.word) >= 2]
        if not terms:
            return {"query": query, "results": []}
        sets = [self.def_index.get(t, set()) for t in terms]
        hits = set.intersection(*sets) if all(sets) else set()
        hits.discard(query)
        # shortest definitions first: closest to being a synonym
        ranked = sorted(hits,
                        key=lambda w: (len(self.definitions[w][0]), w))[:limit]
        return {"query": query, "results": [
            {"word": w, "definition": self.definitions[w][0]}
            for w in ranked]}


def _make_handler(tools: Tools):

    class Handler(BaseHTTPRequestHandler):
        server_version = "DhivehiTools/0.2"

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, obj, code: int = 200) -> None:
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def _read_json(self):
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 2_000_000:
                return None
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return None

        def log_message(self, fmt, *args):
            pass

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "86400")
            self.send_header("Content-Length", "0")
            self.end_headers()

        STATIC_FILES = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/dhivehi.js": ("dhivehi.js",
                            "application/javascript; charset=utf-8"),
            "/sw.js": ("sw.js", "application/javascript; charset=utf-8"),
            "/manifest.json": ("manifest.json",
                               "application/manifest+json; charset=utf-8"),
            "/icon.svg": ("icon.svg", "image/svg+xml"),
            "/fonts/mvtyper.ttf": (os.path.join("fonts", "mvtyper.ttf"),
                                   "font/ttf"),
        }

        def do_GET(self):
            static = self.STATIC_FILES.get(self.path)
            if static is not None:
                name, ctype = static
                with open(os.path.join(STATIC_DIR, name), "rb") as fh:
                    self._send(200, fh.read(), ctype)
            elif self.path == "/api/stats":
                self._send_json({
                    "words": len(tools.spell.lexicon),
                    "synonyms": len(tools.paraphraser.synonyms),
                    "definitions": len(tools.definitions),
                })
            elif self.path == "/api/unknowns":
                with tools.lock:
                    top = tools.unknown_log.most_common(100)
                self._send_json({"unknowns": [
                    {"word": w, "count": c} for w, c in top]})
            else:
                self._send_json({"error": "not found"}, 404)

        def do_POST(self):
            if self.path == "/v2/check":
                self._languagetool_check()
                return
            data = self._read_json()
            if data is None:
                self._send_json({"error": "invalid JSON body"}, 400)
                return
            if self.path == "/api/spell/check":
                with tools.lock:
                    issues = tools.spell.check_text(str(data.get("text", "")))
                    tools.log_unknowns(issues)
                self._send_json({"issues": issues})
            elif self.path == "/api/spell/add":
                words: List[str] = [str(w).strip() for w in data.get("words", [])]
                words = [w for w in words if w]
                if not words:
                    self._send_json({"error": "no words given"}, 400)
                    return
                with tools.lock:
                    tools.spell.add_words(words, freq=50)
                    if tools.user_wordlist:
                        with open(tools.user_wordlist, "a", encoding="utf-8") as fh:
                            for w in words:
                                fh.write(w + "\t50\n")
                self._send_json({"added": words,
                                 "words": len(tools.spell.lexicon)})
            elif self.path == "/api/grammar/check":
                issues = tools.grammar.check(str(data.get("text", "")))
                self._send_json({"issues": issues})
            elif self.path == "/api/paraphrase":
                try:
                    aggressiveness = float(data.get("aggressiveness", 0.5))
                    seed = int(data.get("seed", 0))
                except (TypeError, ValueError):
                    self._send_json({"error": "bad parameters"}, 400)
                    return
                result = tools.paraphraser.paraphrase(
                    str(data.get("text", "")), aggressiveness, seed,
                    modern_only=bool(data.get("modern_only", False)))
                self._send_json(result)
            elif self.path == "/api/define":
                self._send_json(tools.define(str(data.get("q", "")).strip()))
            elif self.path == "/api/reverse":
                self._send_json(
                    tools.reverse_lookup(str(data.get("q", "")).strip()))
            elif self.path == "/api/translit":
                text = str(data.get("text", ""))
                if data.get("to") == "latin":
                    out = thaana_to_latin(text)
                else:
                    out = latin_to_thaana(text)
                self._send_json({"text": out})
            elif self.path == "/api/register":
                text = str(data.get("text", ""))
                if data.get("target") == "informal":
                    out = to_informal(text)
                else:
                    out = to_formal(text)
                self._send_json({"text": out})
            else:
                self._send_json({"error": "not found"}, 404)

        # -- LanguageTool protocol -----------------------------------------

        def _languagetool_check(self):
            """Minimal LanguageTool /v2/check: form-encoded in, LT JSON out.

            Lets existing LT clients (browser add-ons, editors) use this
            server by pointing them at http://127.0.0.1:<port>.
            """
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 2_000_000:
                self._send_json({"error": "bad request"}, 400)
                return
            params = urllib.parse.parse_qs(
                self.rfile.read(length).decode("utf-8"))
            text = params.get("text", [""])[0]

            matches = []
            with tools.lock:
                spell_issues = tools.spell.check_text(text)
                tools.log_unknowns(spell_issues)
            for it in spell_issues:
                matches.append({
                    "message": ("Thaana structure error"
                                if it["status"] == "structure"
                                else "Unknown word"),
                    "shortMessage": "Spelling",
                    "offset": it["start"],
                    "length": it["end"] - it["start"],
                    "replacements": [{"value": s["word"]}
                                     for s in it.get("suggestions", [])],
                    "rule": {"id": "DV_SPELL_" + it["status"].upper(),
                             "description": "Dhivehi spelling",
                             "issueType": "misspelling",
                             "category": {"id": "TYPOS", "name": "Spelling"}},
                })
            for it in tools.grammar.check(text):
                matches.append({
                    "message": it["message"],
                    "shortMessage": it["rule"],
                    "offset": it["start"],
                    "length": it["end"] - it["start"],
                    "replacements": ([{"value": it["replacement"]}]
                                     if "replacement" in it else []),
                    "rule": {"id": "DV_" + it["rule"].upper().replace("-", "_"),
                             "description": it["message"],
                             "issueType": ("style"
                                           if it["severity"] == "style"
                                           else "grammar"),
                             "category": {"id": "GRAMMAR", "name": "Grammar"}},
                })
            matches.sort(key=lambda m: m["offset"])
            self._send_json({
                "software": {"name": "DhivehiTools", "version": "0.3.0"},
                "language": {"name": "Dhivehi", "code": "dv",
                             "detectedLanguage": {"name": "Dhivehi",
                                                  "code": "dv"}},
                "matches": matches,
            })

    return Handler


def create_server(host: str = "127.0.0.1", port: int = 8765,
                  user_wordlist: Optional[str] = None) -> ThreadingHTTPServer:
    tools = Tools(user_wordlist=user_wordlist)
    return ThreadingHTTPServer((host, port), _make_handler(tools))


def serve(host: str = "127.0.0.1", port: int = 8765,
          user_wordlist: Optional[str] = None) -> None:
    httpd = create_server(host, port, user_wordlist)
    print("Dhivehi Tools running at http://%s:%d/  (Ctrl+C to stop)"
          % (host, httpd.server_address[1]))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

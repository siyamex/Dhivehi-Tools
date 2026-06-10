"""Local web front-end for the spell checker.

Runs a small stdlib HTTP server (no dependencies, no network access needed)
that serves a single-page editor and a JSON API:

  GET  /            the editor UI
  GET  /api/stats   {"words": <lexicon size>}
  POST /api/check   {"text": ...}  -> {"issues": [...]}   (offsets included)
  POST /api/word    {"word": ...}  -> per-word result
  POST /api/add     {"words": [...]} -> adds to the lexicon, persists to the
                                        user wordlist file if one is set
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional

from .checker import SpellChecker

STATIC_DIR = os.path.join(os.path.dirname(__file__), "web_static")


def _make_handler(checker: SpellChecker, user_wordlist: Optional[str]):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "DhivehiSpell/0.1"

        # -- helpers ------------------------------------------------------

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            # The UI may be opened from file:// or an editor preview pane
            # rather than from this server; allow those origins in.
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

        def log_message(self, fmt, *args):  # keep the console quiet
            pass

        # -- routes -------------------------------------------------------

        def do_OPTIONS(self):  # CORS preflight for JSON POSTs
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "86400")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                path = os.path.join(STATIC_DIR, "index.html")
                with open(path, "rb") as fh:
                    self._send(200, fh.read(), "text/html; charset=utf-8")
            elif self.path == "/api/stats":
                self._send_json({"words": len(checker.lexicon)})
            else:
                self._send_json({"error": "not found"}, 404)

        def do_POST(self):
            data = self._read_json()
            if data is None:
                self._send_json({"error": "invalid JSON body"}, 400)
                return
            if self.path == "/api/check":
                text = str(data.get("text", ""))
                with lock:
                    issues = checker.check_text(text)
                self._send_json({"issues": issues})
            elif self.path == "/api/word":
                word = str(data.get("word", "")).strip()
                with lock:
                    result = checker.check_word(word)
                self._send_json(result.to_dict())
            elif self.path == "/api/add":
                words: List[str] = [str(w).strip() for w in data.get("words", [])]
                words = [w for w in words if w]
                if not words:
                    self._send_json({"error": "no words given"}, 400)
                    return
                with lock:
                    checker.add_words(words, freq=50)
                    if user_wordlist:
                        with open(user_wordlist, "a", encoding="utf-8") as fh:
                            for w in words:
                                fh.write(w + "\t50\n")
                self._send_json({"added": words, "words": len(checker.lexicon)})
            else:
                self._send_json({"error": "not found"}, 404)

    return Handler


def create_server(host: str = "127.0.0.1", port: int = 8765,
                  checker: Optional[SpellChecker] = None,
                  user_wordlist: Optional[str] = None) -> ThreadingHTTPServer:
    if checker is None:
        extra = [user_wordlist] if user_wordlist and os.path.exists(user_wordlist) else []
        checker = SpellChecker(extra_wordlists=extra)
    handler = _make_handler(checker, user_wordlist)
    return ThreadingHTTPServer((host, port), handler)


def serve(host: str = "127.0.0.1", port: int = 8765,
          user_wordlist: Optional[str] = None) -> None:
    httpd = create_server(host, port, user_wordlist=user_wordlist)
    print("Dhivehi spell checker running at http://%s:%d/  (Ctrl+C to stop)"
          % (host, httpd.server_address[1]))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

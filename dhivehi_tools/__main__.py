"""Dhivehi Tools CLI.

  python -m dhivehi_tools serve [--port 8765]      unified web UI
  python -m dhivehi_tools grammar "TEXT"|--file P  grammar check
  python -m dhivehi_tools paraphrase "TEXT"        paraphrase text

Spell-checking CLI lives in `python -m dhivehi_spell`.
"""

from __future__ import annotations

import argparse
import json
import sys


def cmd_serve(args) -> int:
    from .web import serve
    serve(host=args.host, port=args.port, user_wordlist=args.user_wordlist)
    return 0


def _read_text(args) -> str:
    if getattr(args, "file", None):
        with open(args.file, encoding="utf-8-sig") as fh:
            return fh.read()
    if args.text == "-" or args.text is None:
        return sys.stdin.read()
    return args.text


def cmd_grammar(args) -> int:
    from .grammar import GrammarChecker
    text = _read_text(args)
    issues = GrammarChecker().check(text)
    if args.json:
        print(json.dumps(issues, ensure_ascii=False, indent=2))
    elif not issues:
        print("No grammar issues found.")
    else:
        for it in issues:
            line = "[%d:%d] %s (%s): %s" % (
                it["start"], it["end"], it["rule"], it["severity"], it["message"])
            if "replacement" in it:
                line += "  ->  %r" % it["replacement"]
            print(line)
    return 1 if issues else 0


def cmd_paraphrase(args) -> int:
    from .paraphrase import Paraphraser
    text = _read_text(args)
    result = Paraphraser().paraphrase(text, args.aggressiveness, args.seed)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["text"])
        print("-- swapped %d of %d swappable words (seed %d)"
              % (result["swapped"], result["swappable"], result["seed"]),
              file=sys.stderr)
    return 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="dhivehi_tools",
                                     description="Offline Dhivehi language tools")
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="command", required=True)

    p_srv = sub.add_parser("serve", help="run the unified web UI")
    p_srv.add_argument("--host", default="127.0.0.1")
    p_srv.add_argument("--port", type=int, default=8765)
    p_srv.add_argument("--user-wordlist", default="user_words.tsv")
    p_srv.set_defaults(func=cmd_serve)

    p_gr = sub.add_parser("grammar", help="grammar-check text or a file")
    p_gr.add_argument("text", nargs="?")
    p_gr.add_argument("--file")
    p_gr.set_defaults(func=cmd_grammar)

    p_pp = sub.add_parser("paraphrase", help="paraphrase text")
    p_pp.add_argument("text", nargs="?")
    p_pp.add_argument("--file")
    p_pp.add_argument("--aggressiveness", type=float, default=0.5)
    p_pp.add_argument("--seed", type=int, default=0)
    p_pp.set_defaults(func=cmd_paraphrase)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

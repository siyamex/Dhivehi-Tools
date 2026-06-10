"""Command-line interface.

Usage:
  python -m dhivehi_spell check "TEXT"          check Thaana text given inline
  python -m dhivehi_spell check --file PATH     check a UTF-8 text file
  python -m dhivehi_spell check -               check stdin
  python -m dhivehi_spell suggest WORD          suggestions for one word
  python -m dhivehi_spell validate WORD         structural (orthographic) check
  python -m dhivehi_spell serve                 web UI at http://127.0.0.1:8765

Options:
  --json            machine-readable output
  --wordlist PATH   extra user wordlist(s), repeatable
"""

from __future__ import annotations

import argparse
import json
import sys

from .checker import SpellChecker
from .thaana import parse_units, romanize


def _build_checker(args) -> SpellChecker:
    return SpellChecker(extra_wordlists=args.wordlist or [])


def _print(s: str) -> None:
    sys.stdout.write(s + "\n")


def cmd_check(args) -> int:
    if args.file:
        with open(args.file, encoding="utf-8-sig") as fh:
            text = fh.read()
    elif args.text == "-" or args.text is None:
        text = sys.stdin.read()
    else:
        text = args.text

    checker = _build_checker(args)
    issues = checker.check_text(text)

    if args.json:
        _print(json.dumps(issues, ensure_ascii=False, indent=2))
    elif not issues:
        _print("No spelling issues found.")
    else:
        for issue in issues:
            word = issue["word"]
            line = "[%d:%d] %s (%s) — %s" % (
                issue["start"], issue["end"], word, romanize(word), issue["status"])
            _print(line)
            for err in issue.get("errors", []):
                _print("    structure: %s (at offset %d)" % (err["message"], err["index"]))
            sugg = issue.get("suggestions", [])
            if sugg:
                _print("    suggestions: " + ", ".join(
                    "%s (%s, %.2f)" % (s["word"], romanize(s["word"]), s["cost"])
                    for s in sugg))
    return 1 if issues else 0


def cmd_suggest(args) -> int:
    checker = _build_checker(args)
    result = checker.check_word(args.word)
    if args.json:
        _print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if result.is_correct:
        extra = " (via stem %s)" % result.via if result.via else ""
        _print("%s is spelled correctly%s." % (args.word, extra))
    elif result.suggestions:
        for word, cost in result.suggestions:
            _print("%s\t%s\t%.2f" % (word, romanize(word), cost))
    else:
        _print("No suggestions found.")
    return 0


def cmd_validate(args) -> int:
    units, errors = parse_units(args.word)
    if args.json:
        _print(json.dumps({
            "word": args.word,
            "well_formed": not errors,
            "units": [{"consonant": c, "fili": f} for c, f in units],
            "errors": [e._asdict() for e in errors],
        }, ensure_ascii=False, indent=2))
        return 0 if not errors else 1
    if not errors:
        _print("%s is structurally valid Thaana (%d units, '%s')." % (
            args.word, len(units), romanize(args.word)))
        return 0
    for e in errors:
        _print("offset %d: %s [%s]" % (e.index, e.message, e.code))
    return 1


def cmd_serve(args) -> int:
    from .web import serve
    serve(host=args.host, port=args.port, user_wordlist=args.user_wordlist)
    return 0


def main(argv=None) -> int:
    # Thaana on Windows consoles needs UTF-8 stdout.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="dhivehi_spell",
                                     description="Offline Dhivehi spell checker")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--wordlist", action="append", metavar="PATH",
                        help="extra wordlist file (repeatable)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="check text or a file")
    p_check.add_argument("text", nargs="?", help="text to check, or - for stdin")
    p_check.add_argument("--file", help="UTF-8 text file to check")
    p_check.set_defaults(func=cmd_check)

    p_sugg = sub.add_parser("suggest", help="suggestions for one word")
    p_sugg.add_argument("word")
    p_sugg.set_defaults(func=cmd_suggest)

    p_val = sub.add_parser("validate", help="structural check for one word")
    p_val.add_argument("word")
    p_val.set_defaults(func=cmd_validate)

    p_srv = sub.add_parser("serve", help="run the local web UI")
    p_srv.add_argument("--host", default="127.0.0.1")
    p_srv.add_argument("--port", type=int, default=8765)
    p_srv.add_argument("--user-wordlist", default="user_words.tsv",
                       help="file where words added from the UI are persisted")
    p_srv.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

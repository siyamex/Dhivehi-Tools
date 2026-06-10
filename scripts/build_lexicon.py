"""Convert the Radheef dictionary dump (data-radheef.js) into a lexicon TSV.

Usage:  python scripts/build_lexicon.py [data_raw/data-radheef.js]

The dump is a JS file of the form:  window.RADHEEF=[["word","definition"],...]
Headwords may contain several Thaana words and stray punctuation; every
well-formed Thaana token is harvested.  Tokens that violate Thaana
orthography are skipped (and a sample is reported) so the lexicon stays
consistent with the validator.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhivehi_spell.thaana import parse_units, tokenize  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "..",
                        "dhivehi_spell", "data", "radheef.tsv")


def load_entries(path: str):
    with open(path, encoding="utf-8-sig") as fh:
        raw = fh.read()
    m = re.search(r"=\s*(\[.*\])\s*;?\s*$", raw, re.S)
    if not m:
        raise SystemExit("could not find the RADHEEF array in %s" % path)
    return json.loads(m.group(1))


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "data_raw", "data-radheef.js")
    entries = load_entries(src)

    words = Counter()
    irregular = Counter()
    for entry in entries:
        if not entry or not isinstance(entry, list):
            continue
        headword = str(entry[0])
        tokens = [t.word for t in tokenize(headword)]
        # Single-token headwords are dictionary lemmas (freq 50); tokens from
        # multi-word headwords are still real words but rank lower (freq 30).
        freq = 50 if len(tokens) == 1 else 30
        for tok in tokens:
            if len(tok) < 2:
                continue
            _units, errors = parse_units(tok)
            if errors:
                # Official entry with archaic/dialectal orthography: keep it
                # (exact lookup still works; the lexicon just won't index it
                # for fuzzy suggestions), but at a low frequency.
                irregular[tok] += 1
                words[tok] = max(words[tok], 20)
            else:
                words[tok] = max(words[tok], freq)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("# Generated from Radheef (radheef.siyamex.com) by "
                 "scripts/build_lexicon.py — do not edit by hand.\n")
        for word in sorted(words):
            fh.write("%s\t%d\n" % (word, words[word]))

    print("entries in dump:      %d" % len(entries))
    print("unique words kept:    %d" % len(words))
    print("orthographically irregular (kept, exact-match only): %d" % len(irregular))
    if irregular:
        sample = ", ".join(w for w, _ in irregular.most_common(15))
        print("irregular sample:     %s" % sample)
    print("wrote %s" % os.path.normpath(OUT_PATH))


if __name__ == "__main__":
    main()

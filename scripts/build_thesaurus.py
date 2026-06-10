"""Harvest a Dhivehi thesaurus from the Radheef dump.

Usage:  python scripts/build_thesaurus.py [data_raw/data-radheef.js]

Many Radheef definitions are a single word — i.e. a synonym of the headword
(e.g. ["ހަހަރު","ލޯބި"]). This script collects those pairs (bidirectionally),
keeping only well-formed words that exist in the spell-check lexicon, and
writes dhivehi_tools/data/thesaurus.tsv:  word <TAB> syn1|syn2|...
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhivehi_spell.checker import SpellChecker          # noqa: E402
from dhivehi_spell.thaana import parse_units, tokenize  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "..",
                        "dhivehi_tools", "data", "thesaurus.tsv")

# POS / numbering markers like "(ނ)", "(2)", stray digits and Latin.
_MARKER_RE = re.compile(r"\([^)]*\)|[0-9A-Za-z]+")


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
    lexicon = SpellChecker().lexicon

    def usable(word: str) -> bool:
        return (len(word) >= 2 and word in lexicon
                and not parse_units(word)[1])

    synonyms = defaultdict(set)
    pairs = 0
    for entry in entries:
        if not entry or len(entry) < 2:
            continue
        headword, definition = str(entry[0]).strip(), str(entry[1])
        head_tokens = [t.word for t in tokenize(headword)]
        if len(head_tokens) != 1 or not usable(head_tokens[0]):
            continue
        head = head_tokens[0]
        cleaned = _MARKER_RE.sub(" ", definition)
        def_tokens = [t.word for t in tokenize(cleaned)]
        if len(def_tokens) != 1:
            continue                      # multi-word gloss, not a synonym
        syn = def_tokens[0]
        if syn == head or not usable(syn):
            continue
        synonyms[head].add(syn)
        synonyms[syn].add(head)
        pairs += 1

    # corpus attestation: a synonym seen in the Wikipedia corpus is "modern"
    corpus_counts = {}
    unigrams = os.path.join(os.path.dirname(__file__), "..",
                            "data_raw", "wiki_unigrams.tsv")
    if os.path.exists(unigrams):
        with open(unigrams, encoding="utf-8-sig") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2:
                    corpus_counts[parts[0]] = int(parts[1])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("# Generated from Radheef (radheef.siyamex.com) by "
                 "scripts/build_thesaurus.py — do not edit by hand.\n")
        fh.write("# format: word <TAB> synonym:corpus_count|synonym:count...\n")
        for word in sorted(synonyms):
            entry = "|".join("%s:%d" % (s, corpus_counts.get(s, 0))
                             for s in sorted(synonyms[word]))
            fh.write("%s\t%s\n" % (word, entry))

    print("entries in dump:        %d" % len(entries))
    print("synonym pairs found:    %d" % pairs)
    print("words with synonyms:    %d" % len(synonyms))
    sample = list(sorted(synonyms))[:8]
    for w in sample:
        print("  %s -> %s" % (w, ", ".join(sorted(synonyms[w])[:4])))
    print("wrote %s" % os.path.normpath(OUT_PATH))


if __name__ == "__main__":
    main()

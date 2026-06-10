"""Build frequency and bigram data from the Dhivehi Wikipedia dump.

Usage:  python scripts/build_corpus.py [data_raw/dvwiki-latest-pages-articles.xml.bz2]

Outputs:
  dhivehi_spell/data/corpus.tsv    well-formed words seen >= MIN_COUNT times
                                   that the lexicon doesn't already have,
                                   with corpus counts as frequency
  data_raw/wiki_unigrams.tsv       every Thaana token with its count
  dhivehi_spell/data/bigrams.tsv   Thaana bigrams seen >= MIN_BIGRAM times
"""

from __future__ import annotations

import bz2
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhivehi_spell.checker import SpellChecker          # noqa: E402
from dhivehi_spell.thaana import parse_units, tokenize  # noqa: E402

HERE = os.path.dirname(__file__)
CORPUS_OUT = os.path.join(HERE, "..", "dhivehi_spell", "data", "corpus.tsv")
# .dat, not .tsv: the checker auto-loads every data/*.tsv as a wordlist
BIGRAMS_OUT = os.path.join(HERE, "..", "dhivehi_spell", "data", "bigrams.dat")
UNIGRAMS_OUT = os.path.join(HERE, "..", "data_raw", "wiki_unigrams.tsv")

MIN_COUNT = 3        # new word must appear this often to enter the lexicon
MIN_BIGRAM = 3
MAX_FREQ = 100000

_TEXT_RE = re.compile(r"<text[^>]*>(.*?)</text>", re.S)
_MARKUP_RES = [
    re.compile(r"\{\{[^{}]*\}\}"),                  # templates (two passes)
    re.compile(r"<ref[^>]*>.*?</ref>", re.S),
    re.compile(r"<[^>]+>"),                          # html tags
    re.compile(r"\[\[(?:[^\[\]|]*\|)?([^\[\]]*)\]\]"),  # [[target|label]] -> label
    re.compile(r"&[a-z]+;"),
]


def clean_markup(text: str) -> str:
    for _ in range(2):
        text = _MARKUP_RES[0].sub(" ", text)
    text = _MARKUP_RES[1].sub(" ", text)
    text = _MARKUP_RES[2].sub(" ", text)
    text = _MARKUP_RES[3].sub(r"\1", text)
    text = _MARKUP_RES[4].sub(" ", text)
    return text


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "..", "data_raw", "dvwiki-latest-pages-articles.xml.bz2")
    opener = bz2.open if src.endswith(".bz2") else open
    with opener(src, "rt", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()

    unigrams = Counter()
    bigrams = Counter()
    pages = 0
    for m in _TEXT_RE.finditer(raw):
        pages += 1
        words = [t.word for t in tokenize(clean_markup(m.group(1)))]
        unigrams.update(words)
        bigrams.update(zip(words, words[1:]))

    lexicon = SpellChecker().lexicon
    added = 0
    with open(CORPUS_OUT, "w", encoding="utf-8") as fh:
        fh.write("# Generated from the Dhivehi Wikipedia dump by "
                 "scripts/build_corpus.py — do not edit by hand.\n")
        for word, count in unigrams.most_common():
            if count < MIN_COUNT or len(word) < 2 or word in lexicon:
                continue
            if parse_units(word)[1]:
                continue                      # not well-formed Thaana
            fh.write("%s\t%d\n" % (word, min(count, MAX_FREQ)))
            added += 1

    with open(UNIGRAMS_OUT, "w", encoding="utf-8") as fh:
        for word, count in unigrams.most_common():
            fh.write("%s\t%d\n" % (word, count))

    kept_bigrams = 0
    with open(BIGRAMS_OUT, "w", encoding="utf-8") as fh:
        fh.write("# w1 <TAB> w2 <TAB> count — from the Dhivehi Wikipedia dump.\n")
        for (w1, w2), count in bigrams.most_common():
            if count < MIN_BIGRAM:
                break
            fh.write("%s\t%s\t%d\n" % (w1, w2, count))
            kept_bigrams += 1

    print("pages processed:      %d" % pages)
    print("distinct tokens:      %d" % len(unigrams))
    print("total tokens:         %d" % sum(unigrams.values()))
    print("new lexicon words:    %d  -> %s" % (added, os.path.normpath(CORPUS_OUT)))
    print("bigrams kept:         %d  -> %s" % (kept_bigrams, os.path.normpath(BIGRAMS_OUT)))


if __name__ == "__main__":
    main()

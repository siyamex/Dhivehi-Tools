"""Harvest Dhivehi text from news pages into the corpus pipeline.

Two modes:
  python scripts/build_news_corpus.py --dir data_raw/news/
      process already-saved .html / .txt files (recommended: save pages
      with any crawler or browser, then run this offline)

  python scripts/build_news_corpus.py --url-list urls.txt [--delay 3]
      politely fetch each URL (one request every --delay seconds, custom
      User-Agent, errors skipped) into data_raw/news/ first, then process

Output: data_raw/news_unigrams.tsv and data_raw/news_bigrams.tsv.
Merge into the live data with:  python scripts/merge_corpora.py
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from html.parser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhivehi_spell.thaana import tokenize  # noqa: E402

HERE = os.path.dirname(__file__)
NEWS_DIR = os.path.join(HERE, "..", "data_raw", "news")
UNI_OUT = os.path.join(HERE, "..", "data_raw", "news_unigrams.tsv")
BI_OUT = os.path.join(HERE, "..", "data_raw", "news_bigrams.tsv")

USER_AGENT = "DhivehiToolsCorpusBot/0.1 (offline language tooling)"


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def extract_text(raw: str) -> str:
    if "<" in raw and ">" in raw:
        p = _TextExtractor()
        try:
            p.feed(raw)
            return " ".join(p.parts)
        except Exception:
            pass
    return raw


def fetch(url: str, delay: float) -> None:
    os.makedirs(NEWS_DIR, exist_ok=True)
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".html"
    dest = os.path.join(NEWS_DIR, name)
    if os.path.exists(dest):
        return
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read(5_000_000)
        with open(dest, "wb") as fh:
            fh.write(body)
        print("fetched %s -> %s" % (url, name))
    except Exception as exc:
        print("skip %s (%s)" % (url, exc))
    time.sleep(delay)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=NEWS_DIR)
    ap.add_argument("--url-list", help="file with one URL per line")
    ap.add_argument("--delay", type=float, default=3.0)
    args = ap.parse_args()

    if args.url_list:
        with open(args.url_list, encoding="utf-8-sig") as fh:
            for line in fh:
                url = line.strip()
                if url and not url.startswith("#"):
                    fetch(url, args.delay)

    unigrams, bigrams = Counter(), Counter()
    files = 0
    if os.path.isdir(args.dir):
        for name in sorted(os.listdir(args.dir)):
            path = os.path.join(args.dir, name)
            if not (name.endswith(".html") or name.endswith(".txt")):
                continue
            files += 1
            with open(path, encoding="utf-8", errors="replace") as fh:
                words = [t.word for t in tokenize(extract_text(fh.read()))]
            unigrams.update(words)
            bigrams.update(zip(words, words[1:]))

    with open(UNI_OUT, "w", encoding="utf-8") as fh:
        for w, c in unigrams.most_common():
            fh.write("%s\t%d\n" % (w, c))
    with open(BI_OUT, "w", encoding="utf-8") as fh:
        for (a, b), c in bigrams.most_common():
            if c < 2:
                break
            fh.write("%s\t%s\t%d\n" % (a, b, c))

    print("files processed: %d" % files)
    print("distinct tokens: %d (total %d)"
          % (len(unigrams), sum(unigrams.values())))
    print("wrote %s and %s" % (os.path.normpath(UNI_OUT),
                               os.path.normpath(BI_OUT)))


if __name__ == "__main__":
    main()

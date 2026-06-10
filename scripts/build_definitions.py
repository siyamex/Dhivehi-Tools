"""Extract word -> definition entries from the Radheef dump.

Usage:  python scripts/build_definitions.py [data_raw/data-radheef.js]
Writes dhivehi_tools/data/definitions.tsv:  headword <TAB> definition
(one line per sense; headwords may repeat).
"""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(__file__)
OUT_PATH = os.path.join(HERE, "..", "dhivehi_tools", "data", "definitions.tsv")


def main() -> None:
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "..", "data_raw", "data-radheef.js")
    with open(src, encoding="utf-8-sig") as fh:
        raw = fh.read()
    m = re.search(r"=\s*(\[.*\])\s*;?\s*$", raw, re.S)
    if not m:
        raise SystemExit("could not find the RADHEEF array in %s" % src)
    entries = json.loads(m.group(1))

    count = 0
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("# Generated from Radheef (radheef.siyamex.com) by "
                 "scripts/build_definitions.py — do not edit by hand.\n")
        for entry in entries:
            if not entry or len(entry) < 2:
                continue
            word = str(entry[0]).strip()
            definition = " ".join(str(entry[1]).split())  # collapse whitespace
            if word and definition:
                fh.write("%s\t%s\n" % (word, definition))
                count += 1
    print("definitions written: %d -> %s" % (count, os.path.normpath(OUT_PATH)))


if __name__ == "__main__":
    main()

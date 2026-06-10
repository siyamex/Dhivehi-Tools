"""Export the lexicon as a Hunspell dictionary (dv_MV.dic / dv_MV.aff).

Usage:  python scripts/export_hunspell.py [output_dir=dist]

The .aff encodes:
  - SFX A: the nominal case/plural/eve paradigm from dhivehi_tools.morphology
    (so Hunspell accepts ރަށުގައި when the .dic contains ރަށް)
  - REP: likely error pairs (short<->long fili, consonant confusion sets)
  - TRY: suggestion alphabet ordered by frequency

Install by dropping both files into the Hunspell dictionary folder of
LibreOffice / Firefox / Thunderbird.
"""

from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhivehi_spell.checker import SpellChecker                  # noqa: E402
from dhivehi_spell.thaana import CONFUSION_SETS, FILI_LENGTH_PAIRS  # noqa: E402
from dhivehi_tools.morphology import EVE_RULES, RULES, VERB_RULES  # noqa: E402

FLAG = "A"


def build_aff(words) -> str:
    lines = ["SET UTF-8", "WORDCHARS ހށނރބޅކއވމފދތލގޏސޑޒޓޔޕޖޗޘޙޚޛޜޝޞޟޠޡޢޣޤޥޱަާިީުޫެޭޮޯް", ""]

    # TRY: characters ordered by frequency in the lexicon
    counts = Counter()
    for w in words:
        counts.update(w)
    lines.append("TRY " + "".join(ch for ch, _ in counts.most_common()))
    lines.append("")

    # REP: likely substitutions
    reps = []
    seen = set()
    for a, b in FILI_LENGTH_PAIRS.items():
        if (a, b) not in seen:
            reps.append((a, b))
            seen.add((a, b))
    for group in CONFUSION_SETS:
        members = sorted(group)
        for a in members:
            for b in members:
                if a != b and (a, b) not in seen:
                    reps.append((a, b))
                    seen.add((a, b))
    lines.append("REP %d" % len(reps))
    for a, b in reps:
        lines.append("REP %s %s" % (a, b))
    lines.append("")

    # SFX: the invertible morphology table
    all_rules = list(RULES) + list(VERB_RULES) + list(EVE_RULES)
    lines.append("SFX %s Y %d" % (FLAG, len(all_rules)))
    for remove, append in all_rules:
        strip = remove if remove else "0"
        cond = remove if remove else "."
        lines.append("SFX %s %s %s %s" % (FLAG, strip, append, cond))
    return "\n".join(lines) + "\n"


def main() -> None:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "dist")
    os.makedirs(out_dir, exist_ok=True)

    lexicon = SpellChecker().lexicon
    words = sorted(w for w in lexicon.iter_words() if "\t" not in w)

    dic_path = os.path.join(out_dir, "dv_MV.dic")
    with open(dic_path, "w", encoding="utf-8") as fh:
        fh.write("%d\n" % len(words))
        for w in words:
            fh.write("%s/%s\n" % (w, FLAG))

    aff_path = os.path.join(out_dir, "dv_MV.aff")
    with open(aff_path, "w", encoding="utf-8") as fh:
        fh.write(build_aff(words))

    print("wrote %s (%d words)" % (os.path.normpath(dic_path), len(words)))
    print("wrote %s" % os.path.normpath(aff_path))


if __name__ == "__main__":
    main()

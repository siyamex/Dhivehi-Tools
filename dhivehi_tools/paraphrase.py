"""Offline Dhivehi paraphrasing via the Radheef-derived thesaurus.

Word-level synonym substitution: every replacement candidate comes from the
official dictionary's own definitions, and only words present in the spell
lexicon are ever produced, so a paraphrase can never introduce a misspelling.

`aggressiveness` (0..1) controls how many swappable words actually get
swapped; `seed` makes results reproducible (regenerate by changing it).
"""

from __future__ import annotations

import os
import random
from typing import Dict, List, Optional

from dhivehi_spell.thaana import tokenize

DEFAULT_THESAURUS = os.path.join(os.path.dirname(__file__), "data", "thesaurus.tsv")


MODERN_MIN_COUNT = 3  # corpus occurrences for a synonym to count as modern


class Paraphraser:
    def __init__(self, thesaurus_path: str = DEFAULT_THESAURUS) -> None:
        # word -> list of (synonym, corpus_count)
        self.synonyms: Dict[str, List[tuple]] = {}
        if thesaurus_path and os.path.exists(thesaurus_path):
            self._load(thesaurus_path)

    def _load(self, path: str) -> None:
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) != 2:
                    continue
                word, syns = parts
                entries = []
                for chunk in syns.split("|"):
                    if not chunk:
                        continue
                    if ":" in chunk:
                        syn, _, count = chunk.rpartition(":")
                        entries.append((syn, int(count) if count.isdigit() else 0))
                    else:                      # legacy format without counts
                        entries.append((chunk, 0))
                self.synonyms[word] = entries

    def alternatives(self, word: str, modern_only: bool = False) -> List[str]:
        entries = self.synonyms.get(word, [])
        if modern_only:
            entries = [e for e in entries if e[1] >= MODERN_MIN_COUNT]
        # most-attested first, so auto-swaps prefer current vocabulary
        return [syn for syn, _ in sorted(entries, key=lambda e: -e[1])]

    def paraphrase(self, text: str, aggressiveness: float = 0.5,
                   seed: int = 0, modern_only: bool = False) -> Dict:
        """Rewrite `text`; returns the new text plus swap metadata.

        Every token that *could* be swapped is reported (so a UI can offer
        alternatives), with `used` set when a swap actually happened.
        Offsets in the result refer to the OUTPUT text.
        """
        rng = random.Random(seed)
        aggressiveness = max(0.0, min(1.0, aggressiveness))
        out: List[str] = []
        replacements: List[Dict] = []
        pos = 0          # position in input
        out_len = 0      # length of output so far

        for token in tokenize(text):
            gap = text[pos:token.start]
            out.append(gap)
            out_len += len(gap)
            choices = self.alternatives(token.word, modern_only)
            used: Optional[str] = None
            if choices and rng.random() < aggressiveness:
                used = rng.choice(choices)
            emitted = used if used is not None else token.word
            if choices:
                replacements.append({
                    "start": out_len,
                    "end": out_len + len(emitted),
                    "original": token.word,
                    "choices": choices,
                    "used": used,
                })
            out.append(emitted)
            out_len += len(emitted)
            pos = token.end

        out.append(text[pos:])
        return {
            "text": "".join(out),
            "replacements": replacements,
            "swapped": sum(1 for r in replacements if r["used"]),
            "swappable": len(replacements),
            "seed": seed,
        }

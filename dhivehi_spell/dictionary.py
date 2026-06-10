"""Lexicon storage plus a SymSpell-style deletes index.

The index operates on *units* (consonant+fili pairs), not raw codepoints:
deleting whole units models real Dhivehi typing errors far better than
deleting individual combining marks.

To stay compact with large lexicons (the Radheef dump is ~31k words), the
index encodes each unit as a fixed 2-char block inside a plain string key,
and stores a bare word string until a key actually collides (then a list).
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from .thaana import Unit, parse_units

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DEFAULT_WORDLIST = os.path.join(DATA_DIR, "wordlist.tsv")

UnitKey = Tuple[Tuple[Optional[str], Optional[str]], ...]

# Placeholders for the empty half of a unit in encoded index keys.
_NO_FILI = "\x00"
_NO_CONS = "\x01"


def units_key(units: List[Unit]) -> UnitKey:
    return tuple((u.consonant, u.fili) for u in units)


def encode_units(units: List[Unit]) -> str:
    """Fixed-width (2 chars per unit) string encoding, for index keys."""
    return "".join((u.consonant or _NO_CONS) + (u.fili or _NO_FILI)
                   for u in units)


def _deletes(key: str, max_edits: int) -> Set[str]:
    """All variants of `key` with up to max_edits 2-char units removed."""
    results = {key}
    frontier = {key}
    for _ in range(max_edits):
        nxt = set()
        for k in frontier:
            for i in range(0, len(k), 2):
                nxt.add(k[:i] + k[i + 2:])
        nxt -= results
        results |= nxt
        frontier = nxt
    return results


def edits_allowed(n_units: int) -> int:
    """How many unit-level edits to tolerate for a word of n units."""
    if n_units <= 2:
        return 1
    return 2


class Lexicon:
    def __init__(self) -> None:
        self.words: Dict[str, int] = {}            # word -> frequency
        self._units: Dict[str, UnitKey] = {}       # word -> parsed unit key
        # delete-key -> word, or list of words once a key collides
        self._index: Dict[str, Union[str, List[str]]] = {}

    def __contains__(self, word: str) -> bool:
        return word in self.words

    def __len__(self) -> int:
        return len(self.words)

    def frequency(self, word: str) -> int:
        return self.words.get(word, 0)

    def add(self, word: str, freq: int = 1) -> None:
        word = word.strip()
        if not word:
            return
        if word in self.words:
            self.words[word] = max(self.words[word], freq)
            return
        units, errors = parse_units(word)
        self.words[word] = freq
        self._units[word] = units_key(units)
        if errors:
            # Still findable by exact lookup, but don't index malformed entries.
            return
        index = self._index
        encoded = encode_units(units)
        for dk in _deletes(encoded, edits_allowed(len(units))):
            existing = index.get(dk)
            if existing is None:
                index[dk] = word
            elif isinstance(existing, str):
                index[dk] = [existing, word]
            else:
                existing.append(word)

    def load(self, path: str) -> int:
        """Load a UTF-8 wordlist: one word per line, optional <TAB>frequency."""
        count = 0
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                word = parts[0].strip()
                freq = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else 1
                self.add(word, freq)
                count += 1
        return count

    def candidates(self, units: List[Unit]) -> Set[str]:
        """Dictionary words plausibly within edit range of the given units."""
        found: Set[str] = set()
        encoded = encode_units(units)
        index = self._index
        for dk in _deletes(encoded, edits_allowed(len(units))):
            hit = index.get(dk)
            if hit is None:
                continue
            if isinstance(hit, str):
                found.add(hit)
            else:
                found.update(hit)
        return found

    def unit_key(self, word: str) -> UnitKey:
        return self._units[word]

    def iter_words(self) -> Iterable[str]:
        return iter(self.words)

"""Thaana script utilities: character classes, tokenization, unit parsing,
and orthographic (structural) validation for Dhivehi.

A well-formed Dhivehi word is a sequence of *units*, where each unit is a
consonant followed by exactly one fili (vowel sign) or sukun.  The single
systematic exception is the prenasalized stop: a bare noonu (no diacritic)
is valid immediately before one of the voiced stops baa, daviyani, dhaalu,
gaafu (e.g. so it appears in words like 'kan'du' / 'han'dhu').
"""

from __future__ import annotations

import re
from typing import List, NamedTuple, Optional, Tuple

# --- character classes -----------------------------------------------------

CONSONANTS = frozenset(chr(c) for c in range(0x0780, 0x07A6)) | {"ޱ"}
FILI = frozenset(chr(c) for c in range(0x07A6, 0x07B1))  # includes sukun
SUKUN = "ް"
NOONU = "ނ"
ALIFU = "އ"

# Voiced stops that license a preceding bare (diacritic-less) noonu.
PRENASAL_FOLLOWERS = frozenset("ބޑދގ")  # baa daviyani dhaalu gaafu

# Short <-> long vowel pairs (cheap substitutions for the suggester).
FILI_LENGTH_PAIRS = {
    "ަ": "ާ", "ާ": "ަ",  # a / aa
    "ި": "ީ", "ީ": "ި",  # i / ee
    "ު": "ޫ", "ޫ": "ު",  # u / oo
    "ެ": "ޭ", "ޭ": "ެ",  # e / ey
    "ޮ": "ޯ", "ޯ": "ޮ",  # o / oa
}

# Consonants that sound alike in spoken Dhivehi (mostly Arabic-loan letters);
# misusing one for another is the most common class of Dhivehi misspelling.
CONFUSION_SETS = [
    frozenset("ހޙޚ"),          # haa / hhaa / khaa
    frozenset("ސޘޞ"),          # seenu / ttaa(th) / saadhu
    frozenset("ށޝ"),                # shaviyani / sheenu
    frozenset("ޒޛޟޡޜ"),  # zaviyani / thaalu / daadhu / zo / zaa
    frozenset("ތޠ"),                # thaa / to
    frozenset("އޢ"),                # alifu / ainu
    frozenset("ގޣ"),                # gaafu / ghainu
    frozenset("ކޤ"),                # kaafu / qaafu
    frozenset("ވޥ"),                # vaavu / waavu
    frozenset("ނޏޱ"),          # noonu / gnaviyani / naa
]

_CONFUSION_LOOKUP = {}
for _group in CONFUSION_SETS:
    for _ch in _group:
        _CONFUSION_LOOKUP[_ch] = _group


def same_confusion_set(a: str, b: str) -> bool:
    return b in _CONFUSION_LOOKUP.get(a, ())


# Romanization (Malé Latin-ish), used only for debug/display.
_LATIN = {
    "ހ": "h", "ށ": "sh", "ނ": "n", "ރ": "r", "ބ": "b",
    "ޅ": "lh", "ކ": "k", "އ": "", "ވ": "v", "މ": "m",
    "ފ": "f", "ދ": "dh", "ތ": "th", "ލ": "l", "ގ": "g",
    "ޏ": "gn", "ސ": "s", "ޑ": "d", "ޒ": "z", "ޓ": "t",
    "ޔ": "y", "ޕ": "p", "ޖ": "j", "ޗ": "ch", "ޘ": "th",
    "ޙ": "h", "ޚ": "kh", "ޛ": "z", "ޜ": "zh", "ޝ": "sh",
    "ޞ": "s", "ޟ": "z", "ޠ": "t", "ޡ": "z", "ޢ": "a",
    "ޣ": "gh", "ޤ": "q", "ޥ": "w", "ޱ": "n",
    "ަ": "a", "ާ": "aa", "ި": "i", "ީ": "ee", "ު": "u",
    "ޫ": "oo", "ެ": "e", "ޭ": "ey", "ޮ": "o", "ޯ": "oa",
    "ް": "",
}


def romanize(word: str) -> str:
    return "".join(_LATIN.get(ch, ch) for ch in word)


# --- tokenization ----------------------------------------------------------

# Thaana block U+0780-U+07B1, plus ZWNJ/ZWJ which may appear inside words.
_ZWNJ, _ZWJ = chr(0x200C), chr(0x200D)
_TOKEN_RE = re.compile("[%s-%s%s%s]+" % (chr(0x0780), chr(0x07B1), _ZWNJ, _ZWJ))
_ZW_RE = re.compile("[%s%s]" % (_ZWNJ, _ZWJ))


class Token(NamedTuple):
    word: str
    start: int
    end: int


def tokenize(text: str) -> List[Token]:
    """Return Thaana word runs with their offsets in the original text."""
    tokens = []
    for m in _TOKEN_RE.finditer(text):
        word = _ZW_RE.sub("", m.group())
        if word:
            tokens.append(Token(word, m.start(), m.end()))
    return tokens


# --- unit parsing & validation ----------------------------------------------


class Unit(NamedTuple):
    consonant: Optional[str]  # None for a stray fili
    fili: Optional[str]       # None for a bare consonant (prenasal noonu, or an error)


class StructureError(NamedTuple):
    index: int      # codepoint offset inside the word
    code: str       # machine-readable error code
    message: str


def parse_units(word: str) -> Tuple[List[Unit], List[StructureError]]:
    """Split a word into (consonant, fili) units, collecting structural errors.

    Parsing is lenient: malformed input still yields units (with a None slot)
    so the suggestion engine can run a distance computation against it.
    """
    units: List[Unit] = []
    errors: List[StructureError] = []
    i, n = 0, len(word)
    while i < n:
        ch = word[i]
        if ch in CONSONANTS:
            if i + 1 < n and word[i + 1] in FILI:
                units.append(Unit(ch, word[i + 1]))
                i += 2
                continue
            # bare consonant: valid only as prenasal noonu before b/d/dh/g
            nxt = word[i + 1] if i + 1 < n else None
            if ch == NOONU and nxt in PRENASAL_FOLLOWERS:
                units.append(Unit(ch, None))
            else:
                units.append(Unit(ch, None))
                errors.append(StructureError(
                    i, "missing-fili",
                    "consonant has no fili or sukun (every Thaana consonant "
                    "needs a diacritic, except noonu before b/d/dh/g)"))
            i += 1
        elif ch in FILI:
            units.append(Unit(None, ch))
            errors.append(StructureError(
                i, "orphan-fili",
                "fili without a consonant to sit on"))
            i += 1
        else:
            errors.append(StructureError(i, "non-thaana", "unexpected character"))
            i += 1
    return units, errors


def is_well_formed(word: str) -> bool:
    return not parse_units(word)[1]

"""Register conversion: formal written Dhivehi (-eve sentences) <-> informal.

to_formal: attaches the sentence-final particle eve to the last word of each
sentence (using the same morphophonology as the grammar checker) and ensures
terminal punctuation.

to_informal: strips sentence-final eve, including the common fused forms:
  ކުރިއެވެ -> ކުރި       (plain attachment)
  ކަމަށެވެ -> ކަމަށް      (sukun fusion)
  ގައެވެ   -> ގައި       (އި contraction)
  ދިޔައީމެވެ -> ދިޔައީ   (first-person -މެވެ)
  ކުރަމެވެ  -> ކުރަން     (first-person present -އަމެވެ)

This is a best-effort surface transform — it handles the regular sentence-
final morphology, not full verb conjugation.
"""

from __future__ import annotations

import re
from typing import List

from dhivehi_spell.thaana import SUKUN, tokenize

from .grammar import EVE_ENDING, merge_eve

_SENTENCE_RE = re.compile("[^.!؟\n]+[.!؟]?\n?")

# (surface ending, replacement) — order matters, longest/most specific first
_INFORMAL_RULES = [
    ("ީމެވެ", "ީ"),       # ދިޔައީމެވެ -> ދިޔައީ
    ("ަމެވެ", "ަން"),      # ކުރަމެވެ  -> ކުރަން
    ("ގައެވެ", "ގައި"),    # ގައެވެ    -> ގައި
    ("އެވެ", ""),           # ކުރިއެވެ  -> ކުރި
    ("ެވެ", SUKUN),         # ކަމަށެވެ  -> ކަމަށް
]


def _convert(text: str, fn) -> str:
    out: List[str] = []
    pos = 0
    for m in _SENTENCE_RE.finditer(text):
        seg = m.group()
        toks = tokenize(seg)
        if toks:
            last = toks[-1]
            new_word = fn(last.word)
            if new_word != last.word:
                seg = seg[:last.start] + new_word + seg[last.end:]
        out.append(text[pos:m.start()])
        out.append(seg)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def to_formal(text: str) -> str:
    def formalize(word: str) -> str:
        if word.endswith(EVE_ENDING):
            return word                       # already formal
        return merge_eve(word)
    return _convert(text, formalize)


def to_informal(text: str) -> str:
    def informalize(word: str) -> str:
        for ending, repl in _INFORMAL_RULES:
            if word.endswith(ending) and len(word) > len(ending) + 1:
                return word[: len(word) - len(ending)] + repl
        return word
    return _convert(text, informalize)

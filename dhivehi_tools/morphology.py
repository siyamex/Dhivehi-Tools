"""Dhivehi nominal morphology: case/number inflection as invertible rules.

Each rule is a pair (stem_suffix, inflected_suffix): a stem ending with
`stem_suffix` forms the inflection by replacing that ending with
`inflected_suffix`.  Because rules are pure suffix-replacements, the same
table drives three things:

  generate(stem)        stem  -> all inflected surface forms
  analyze(word, known)  word  -> dictionary stems that could underlie it
  (scripts/export_hunspell.py turns the table into Hunspell SFX rules)

Covered: the common case endings (genitive ގެ, locative ގައި, dative އަށް,
ablative އިން, indefinite އެއް, focus އަކީ/އަކަށް/އަކު…), plurals (ތައް and
the ތަކު- oblique series), the sociative ާއި, the stem mutations ސް→ހ and
ން→މ (ބަސް→ބަހުގެ, ނަން→ނަމެއް), and the sentence-final particle އެވެ.
Verb conjugation is NOT modelled (no reliable POS data) — corpus loading
covers frequent conjugated forms instead.
"""

from __future__ import annotations

from typing import Callable, Iterable, List, Set, Tuple

SUKUN = "ް"

# ---------------------------------------------------------------------------
# Rule table: (stem_suffix, inflected_suffix)
# ---------------------------------------------------------------------------

_CASE_TAILS_AFTER_U = ["ގައި", "ގެ", "ން"]          # oblique-u series
_CASE_TAILS_VOWELED = [                                  # direct-vowel series
    ("ަށް",),    ("ެއް",),   ("ަކީ",),  ("ަކަށް",),
    ("ަކުން",),  ("ަކު",),   ("ާ",),    ("ާއި",),
]

RULES: List[Tuple[str, str]] = []

# -- sukun-final stems: ރަށް -> ރަށުގައި / ރަށަށް / ރަށެއް ...
for tail in _CASE_TAILS_AFTER_U:
    RULES.append((SUKUN, "ު" + tail))
for (tail,) in _CASE_TAILS_VOWELED:
    RULES.append((SUKUN, tail))

# -- mutation ސް -> ހ (ބަސް -> ބަހުގެ, ބަހަށް, ބަހެއް ...)
for tail in _CASE_TAILS_AFTER_U:
    RULES.append(("ސް", "ހު" + tail))
for (tail,) in _CASE_TAILS_VOWELED:
    RULES.append(("ސް", "ހ" + tail))

# -- mutation ން -> މ (ނަން -> ނަމުގެ, ނަމަށް, ނަމެއް ...)
for tail in _CASE_TAILS_AFTER_U:
    RULES.append(("ން", "މު" + tail))
for (tail,) in _CASE_TAILS_VOWELED:
    RULES.append(("ން", "މ" + tail))

# -- u-final stems: މަގު -> މަގުގެ, މަގަށް, މަގެއް ...
RULES += [("ު", "ު" + t) for t in _CASE_TAILS_AFTER_U]
RULES += [("ު", t) for (t,) in _CASE_TAILS_VOWELED]

# -- i-final stems: ދޯނި -> ދޯނީގެ / ދޯނީގައި / ދޯނިން / ދޯނީން
RULES += [("ި", "ީ" + t) for t in _CASE_TAILS_AFTER_U[:2]]
RULES += [("ި", "ިން"), ("ި", "ީން")]

# -- a-final stems: ވާހަކަ -> ވާހަކައިގެ / ވާހަކައަށް / ވާހަކައެއް ...
RULES += [("ަ", "ައި" + t) for t in ("ގެ", "ގައި")]
RULES += [("ަ", "ައިން")]
RULES += [("ަ", "ަ" + "އ" + t) for (t,) in _CASE_TAILS_VOWELED[:6]]

# -- e-final stems: ގެ -> ގޭގެ / ގޭގައި / ގެއަށް / ގެއެއް / ގެއިން
RULES += [("ެ", "ޭ" + t) for t in ("ގެ", "ގައި")]
RULES += [("ެ", "ެއަށް"), ("ެ", "ެއެއް"), ("ެ", "ެއިން"), ("ެ", "ެއަކީ")]

# -- long-vowel-final stems: ފަޅޯ -> ފަޅޯގެ / ފަޅޯއެއް ...
for v in ("ާ", "ީ", "ޫ", "ޭ", "ޯ"):
    RULES += [(v, v + "ގެ"), (v, v + "ގައި"),
              (v, v + "އަށް"), (v, v + "އެއް"), (v, v + "އިން")]

# -- plurals attach to the unchanged stem (ރަށްތައް, ވާހަކަތައް ...)
_PLURAL_TAILS = ["ތައް", "ތަކުގެ", "ތަކުގައި", "ތަކަށް", "ތަކުން",
                 "ތަކެއް", "ތަކަކީ", "ތަކަކަށް"]
RULES += [("", t) for t in _PLURAL_TAILS]

# -- sentence-final particle eve (matches grammar.merge_eve)
EVE_RULES: List[Tuple[str, str]] = [
    ("", "އެވެ"),        # ކުރި   -> ކުރިއެވެ
    (SUKUN, "ެވެ"),      # ކަމަށް -> ކަމަށެވެ
    ("އި", "އެވެ"),      # ގައި   -> ގައެވެ
]

# ---------------------------------------------------------------------------
# Verb conjugation: the regular -ުން class (Radheef verb lemmas are verbal
# nouns: ކުރުން "doing", ބުނުން "saying").  Pure suffix replacements only —
# stem-internal vowel alternations (ހެދުން -> ހަދަނީ) and irregular perfects
# (ކޮށްފި) are NOT modelled; the corpus covers their frequent forms.
# ---------------------------------------------------------------------------

VERB_RULES: List[Tuple[str, str]] = [
    ("ުން", "ަނީ"),       # present focus     ކުރުން -> ކުރަނީ
    ("ުން", "ަން"),       # infinitive/intent ކުރުން -> ކުރަން
    ("ުން", "ި"),          # past              ކުރުން -> ކުރި
    ("ުން", "ީ"),          # past focus        ކުރުން -> ކުރީ
    ("ުން", "ާ"),          # participle        ކުރުން -> ކުރާ
    ("ުން", "ާނެ"),       # future            ކުރުން -> ކުރާނެ
    ("ުން", "ާނީ"),       # future focus      ކުރުން -> ކުރާނީ
    ("ުން", "ޭ"),          # imperative/hab.   ކުރުން -> ކުރޭ
    ("ުން", "ަމުން"),     # progressive       ކުރުން -> ކުރަމުން
    ("ުން", "ެވޭ"),       # potential/passive ކުރުން -> ކުރެވޭ
    ("ުން", "ެވުނު"),     # passive past      ކުރުން -> ކުރެވުނު
    ("ުން", "ެވުން"),     # passive v.noun    ކުރުން -> ކުރެވުން
    ("ުން", "ުވުން"),     # causative v.noun  ހެދުން -> ހެދުވުން
    ("ުން", "ާތީ"),       # because-form      ކުރުން -> ކުރާތީ
    ("ުން", "ިއްޖެ"),     # perfective        ވުން   -> ވިއްޖެ
]

_MIN_STEM = 2  # codepoints


def generate(stem: str, rules: Iterable[Tuple[str, str]] = None) -> Set[str]:
    """All inflected surface forms of `stem` (excluding the stem itself)."""
    forms: Set[str] = set()
    for remove, append in (rules if rules is not None else RULES):
        if remove and not stem.endswith(remove):
            continue
        base = stem[: len(stem) - len(remove)] if remove else stem
        if len(base) >= 1:
            forms.add(base + append)
    forms.discard(stem)
    return forms


def _invert(word: str, rules: Iterable[Tuple[str, str]]) -> Set[str]:
    stems: Set[str] = set()
    for remove, append in rules:
        if not word.endswith(append):
            continue
        base = word[: len(word) - len(append)]
        stem = base + remove
        if len(stem) >= _MIN_STEM and stem != word:
            stems.add(stem)
    return stems


def analyze(word: str, known: Callable[[str], bool]) -> List[str]:
    """Dictionary stems that could underlie `word`, best-effort.

    Tries: direct case/plural inflection; the eve particle; and eve stacked
    on top of an inflection (ރަށުގައެވެ -> ރަށުގައި -> ރަށް).
    """
    hits: List[str] = []
    seen: Set[str] = set()

    def consider(stem: str) -> None:
        if stem not in seen and known(stem):
            seen.add(stem)
            hits.append(stem)

    for stem in _invert(word, RULES):
        consider(stem)
    for stem in _invert(word, VERB_RULES):
        consider(stem)
    for de_eved in _invert(word, EVE_RULES):
        consider(de_eved)
        for stem in _invert(de_eved, RULES):
            consider(stem)
        for stem in _invert(de_eved, VERB_RULES):
            consider(stem)
    return hits

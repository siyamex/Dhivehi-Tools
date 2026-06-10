"""Thaana <-> Latin transliteration (Malé Latin convention).

thaana_to_latin: per-character mapping (reuses dhivehi_spell.thaana data).
latin_to_thaana: greedy longest-match parser — digraph consonants first
(th, dh, lh, sh, gn, ch, kh, gh), then long vowels (aa, ee, oo, ey, oa),
then singles.  A consonant with no following vowel gets sukun; a vowel with
no preceding consonant rides on alifu.  An apostrophe after n yields the
bare prenasal noonu (kan'du -> ކަނޑު).
"""

from __future__ import annotations

from dhivehi_spell.thaana import CONSONANTS, FILI, SUKUN, romanize

# consonant romanizations, longest first for greedy matching
_LAT_CONS = [
    ("lh", "ޅ"), ("sh", "ށ"), ("th", "ތ"), ("dh", "ދ"), ("gn", "ޏ"),
    ("ch", "ޗ"), ("kh", "ޚ"), ("gh", "ޣ"), ("zh", "ޜ"),
    ("h", "ހ"), ("n", "ނ"), ("r", "ރ"), ("b", "ބ"), ("k", "ކ"),
    ("v", "ވ"), ("m", "މ"), ("f", "ފ"), ("l", "ލ"), ("g", "ގ"),
    ("s", "ސ"), ("d", "ޑ"), ("z", "ޒ"), ("t", "ޓ"), ("y", "ޔ"),
    ("p", "ޕ"), ("j", "ޖ"), ("w", "ޥ"), ("q", "ޤ"), ("x", "ކްސ"),
]
# vowel romanizations, longest first
_LAT_VOWELS = [
    ("aa", "ާ"), ("ee", "ީ"), ("oo", "ޫ"), ("ey", "ޭ"), ("oa", "ޯ"),
    ("ai", "ަ" + "އ" + "ި"),       # kai -> ކައި
    ("a", "ަ"), ("i", "ި"), ("u", "ު"), ("e", "ެ"), ("o", "ޮ"),
]


def thaana_to_latin(text: str) -> str:
    return romanize(text)


def latin_to_thaana(text: str) -> str:
    out = []
    i, n = 0, len(text)
    lower = text.lower()
    pending_consonant = None     # consonant waiting for its vowel

    def flush(vowel: str = SUKUN) -> None:
        nonlocal pending_consonant
        if pending_consonant is not None:
            out.append(pending_consonant + vowel)
            pending_consonant = None

    while i < n:
        # prenasal marker: n' -> bare noonu
        if lower.startswith("n'", i):
            flush()
            out.append("ނ")
            i += 2
            continue
        matched = False
        for lat, cons in _LAT_CONS:
            if lower.startswith(lat, i):
                flush()                      # previous consonant had no vowel
                # Malé Latin: word-final "h" is shaviyani-sukun (varah -> ވަރަށް)
                if lat == "h" and (i + 1 >= n or not lower[i + 1].isalpha()):
                    cons = "ށ"
                pending_consonant = cons
                i += len(lat)
                matched = True
                break
        if matched:
            continue
        for lat, fili in _LAT_VOWELS:
            if lower.startswith(lat, i):
                if pending_consonant is not None:
                    if len(fili) > 1:        # composite like 'ai'
                        out.append(pending_consonant + fili)
                        pending_consonant = None
                    else:
                        flush(fili)
                else:
                    # vowel-initial: rides on alifu
                    if len(fili) > 1:
                        out.append("އ" + fili[0] + fili[1:])
                    else:
                        out.append("އ" + fili)
                i += len(lat)
                matched = True
                break
        if matched:
            continue
        flush()
        out.append(text[i])                  # spaces, punctuation, digits
        i += 1
    flush()
    return "".join(out)

"""The spell checker: ties together tokenization, structural validation,
lexicon lookup, suffix heuristics, and suggestion ranking.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from .dictionary import DATA_DIR, DEFAULT_WORDLIST, Lexicon, units_key
from .suggest import rank_suggestions
from .thaana import SUKUN, parse_units, tokenize

# Common case endings / clitics, longest first.  Fili-initial forms cover
# the surface shape after a consonant-final stem fuses with the suffix
# (e.g. 'fotheh' = 'foiy' + indefinite: the sukun is replaced by the fili).
SUFFIXES = [
    "ުގައި", "ގައި", "އަކަށް", "ަކަށް", "އަކީ", "ަކީ", "އެއް", "ެއް",
    "ތަކުގެ", "ތަކަށް", "ތައް", "އަށް", "ަށް", "އިން", "ުން", "ުގެ", "ގެ",
    "ާއި", "ަކު", "ން",
]

UBUFILI = "ު"


class WordResult:
    __slots__ = ("word", "status", "errors", "suggestions", "via")

    def __init__(self, word: str, status: str,
                 errors: Optional[list] = None,
                 suggestions: Optional[list] = None,
                 via: Optional[str] = None) -> None:
        self.word = word
        self.status = status          # "ok" | "ok-derived" | "structure" | "unknown"
        self.errors = errors or []
        self.suggestions = suggestions or []
        self.via = via                # stem that validated a suffixed form

    @property
    def is_correct(self) -> bool:
        return self.status in ("ok", "ok-derived")

    def to_dict(self) -> Dict:
        d = {"word": self.word, "status": self.status}
        if self.errors:
            d["errors"] = [
                {"index": e.index, "code": e.code, "message": e.message}
                for e in self.errors
            ]
        if self.suggestions:
            d["suggestions"] = [{"word": w, "cost": c} for w, c in self.suggestions]
        if self.via:
            d["via"] = self.via
        return d


class SpellChecker:
    def __init__(self, wordlist: Optional[str] = DEFAULT_WORDLIST,
                 extra_wordlists: Optional[List[str]] = None,
                 max_suggestions: int = 5) -> None:
        self.lexicon = Lexicon()
        self.max_suggestions = max_suggestions
        if wordlist == DEFAULT_WORDLIST:
            # default: load every bundled lexicon (seed list, Radheef, ...)
            for name in sorted(os.listdir(DATA_DIR)):
                if name.endswith(".tsv"):
                    self.lexicon.load(os.path.join(DATA_DIR, name))
        elif wordlist:
            self.lexicon.load(wordlist)
        for path in extra_wordlists or []:
            if os.path.exists(path):
                self.lexicon.load(path)
        self.bigrams: Dict[tuple, int] = {}
        bigram_path = os.path.join(DATA_DIR, "bigrams.dat")
        if wordlist == DEFAULT_WORDLIST and os.path.exists(bigram_path):
            with open(bigram_path, encoding="utf-8-sig") as fh:
                for line in fh:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) == 3 and not line.startswith("#"):
                        self.bigrams[(parts[0], parts[1])] = int(parts[2])

    # -- lookup helpers -----------------------------------------------------

    def _known(self, word: str) -> Optional[str]:
        """Return the lexicon entry that justifies `word`, if any."""
        if word in self.lexicon:
            return word
        try:
            from dhivehi_tools.morphology import analyze
        except ImportError:                      # standalone dhivehi_spell
            analyze = None
        if analyze is not None:
            stems = analyze(word, lambda s: s in self.lexicon)
            if stems:
                return stems[0]
        # fallback: naive longest-suffix stripping
        for suffix in SUFFIXES:
            if not word.endswith(suffix):
                continue
            stem = word[: -len(suffix)]
            if len(stem) < 2:
                continue
            if stem in self.lexicon:
                return stem
            if stem.endswith(UBUFILI) and stem[:-1] + SUKUN in self.lexicon:
                return stem[:-1] + SUKUN
            units, errs = parse_units(stem)
            if errs and errs[-1].code == "missing-fili" \
                    and stem + SUKUN in self.lexicon:
                return stem + SUKUN
        return None

    def _compound(self, word: str) -> Optional[str]:
        """Accept a joined compound when both halves are dictionary words."""
        units, errors = parse_units(word)
        if errors or len(units) < 5:
            return None
        # unit i starts at codepoint offset = sum of unit widths before it
        offset = 0
        for i, u in enumerate(units):
            width = 1 if u.fili is None else 2
            if 2 <= i <= len(units) - 2:
                left, right = word[:offset], word[offset:]
                if left in self.lexicon and right in self.lexicon:
                    return "%s + %s" % (left, right)
            offset += width
        return None

    def _suggest(self, word: str, prev: Optional[str] = None,
                 nxt: Optional[str] = None) -> List:
        units, _errors = parse_units(word)
        cands = self.lexicon.candidates(units)
        triples = ((w, self.lexicon.unit_key(w), self.lexicon.frequency(w))
                   for w in cands)
        ranked = rank_suggestions(units_key(units), triples,
                                  limit=self.max_suggestions * 3)
        if self.bigrams and (prev or nxt):
            # context bonus: a candidate that forms a known bigram with a
            # neighbour ranks ahead of equally-distant alternatives
            def score(item):
                cand, cost = item
                bonus = 0.0
                if prev and (prev, cand) in self.bigrams:
                    bonus += 0.45
                if nxt and (cand, nxt) in self.bigrams:
                    bonus += 0.45
                return cost - bonus
            ranked.sort(key=score)
        return ranked[: self.max_suggestions]

    # -- public API ----------------------------------------------------------

    def check_word(self, word: str, prev: Optional[str] = None,
                   nxt: Optional[str] = None) -> WordResult:
        # An exact lexicon hit trumps the structural heuristic: official
        # dictionaries contain archaic/dialectal spellings (e.g. bare noonu
        # outside prenasalization) that are valid despite breaking the rule.
        if word in self.lexicon:
            return WordResult(word, "ok")
        units, errors = parse_units(word)
        if errors:
            return WordResult(word, "structure", errors=errors,
                              suggestions=self._suggest(word, prev, nxt))
        justification = self._known(word)
        if justification:
            return WordResult(word, "ok-derived", via=justification)
        compound = self._compound(word)
        if compound:
            return WordResult(word, "ok-derived", via=compound)
        return WordResult(word, "unknown",
                          suggestions=self._suggest(word, prev, nxt))

    def check_text(self, text: str,
                   real_word_check: bool = True) -> List[Dict]:
        """Check every Thaana word in `text`; return issues with offsets."""
        issues = []
        tokens = tokenize(text)
        for i, token in enumerate(tokens):
            prev = tokens[i - 1].word if i > 0 else None
            nxt = tokens[i + 1].word if i + 1 < len(tokens) else None
            result = self.check_word(token.word, prev, nxt)
            if not result.is_correct:
                d = result.to_dict()
                d["start"], d["end"] = token.start, token.end
                issues.append(d)
            elif real_word_check and result.status == "ok":
                alt = self._real_word_suspect(token.word, prev, nxt)
                if alt:
                    issues.append({
                        "word": token.word, "status": "context",
                        "suggestions": [{"word": alt, "cost": 0.4}],
                        "start": token.start, "end": token.end,
                    })
        return issues

    # how much more contextual evidence an alternative needs (bigram counts)
    REAL_WORD_MIN_EVIDENCE = 8

    def _real_word_suspect(self, word: str, prev: Optional[str],
                           nxt: Optional[str]) -> Optional[str]:
        """A real-but-wrong-in-context word: flag only when this word has
        ZERO bigram support with its neighbours while a single-fili-swap
        sibling has strong support.  Conservative by design."""
        if not self.bigrams or (prev is None and nxt is None):
            return None

        def support(w: str) -> int:
            s = 0
            if prev:
                s += self.bigrams.get((prev, w), 0)
            if nxt:
                s += self.bigrams.get((w, nxt), 0)
            return s

        if support(word) > 0:
            return None
        from .thaana import FILI_LENGTH_PAIRS
        best, best_support = None, 0
        chars = list(word)
        for i, ch in enumerate(chars):
            paired = FILI_LENGTH_PAIRS.get(ch)
            if not paired:
                continue
            cand = "".join(chars[:i]) + paired + "".join(chars[i + 1:])
            if cand == word or cand not in self.lexicon:
                continue
            s = support(cand)
            if s > best_support:
                best, best_support = cand, s
        if best is not None and best_support >= self.REAL_WORD_MIN_EVIDENCE:
            return best
        return None

    def add_words(self, words: List[str], freq: int = 1) -> None:
        for w in words:
            self.lexicon.add(w, freq)

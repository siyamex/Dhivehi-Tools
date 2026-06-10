"""Rule-based Dhivehi grammar and style checker.

Rules (all offline, no models):

  thaana-comma       Latin "," after a Thaana word -> "،"      (error)
  thaana-question    Latin "?" after a Thaana word -> "؟"      (error)
  thaana-semicolon   Latin ";" after a Thaana word -> "؛"      (error)
  space-before-punct " ،" -> "،"                                (error)
  space-after-punct  "،word" -> "، word"                        (warning)
  double-space       collapse runs of spaces                    (style)
  repeated-word      "word word" (identical, adjacent)          (warning)
  detached-eve       "ކުރި އެވެ" -> "ކުރިއެވެ" — the sentence-final
                     particle eve must attach to the verb; a final sukun
                     fuses (ކަމަށް + އެވެ -> ކަމަށެވެ)            (error)
  formal-register    if most sentences end with -ެވެ (formal written
                     register), flag sentences that do not       (style)
  long-sentence      more than 40 words                          (style)

Each issue: {rule, severity, message, start, end, replacement?} where
[start, end) indexes the original text and `replacement` (when present) can
be spliced in directly.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from dhivehi_spell.thaana import SUKUN, tokenize

EVE = "އެވެ"
EVE_ENDING = "ެވެ"

_THAANA_LETTER = "[%s-%s]" % (chr(0x0780), chr(0x07B1))
_PUNCT_MAP = [
    (",", "،", "thaana-comma", "use the Thaana comma (،) in Dhivehi text"),
    ("?", "؟", "thaana-question", "use the Thaana question mark (؟) in Dhivehi text"),
    (";", "؛", "thaana-semicolon", "use the Thaana semicolon (؛) in Dhivehi text"),
]
_ALL_PUNCT = ".،؛؟!"

_SPACE_BEFORE_RE = re.compile(" +([%s])" % re.escape(_ALL_PUNCT))
_SPACE_AFTER_RE = re.compile("([%s])(?=%s)" % (re.escape(_ALL_PUNCT), _THAANA_LETTER))
_DOUBLE_SPACE_RE = re.compile("  +")
_SENTENCE_RE = re.compile("[^.!؟\n]+[.!؟]?")

LONG_SENTENCE_WORDS = 40


def merge_eve(word: str) -> str:
    """Attach the sentence-final particle eve to a word."""
    if word.endswith(SUKUN):
        return word[:-1] + EVE_ENDING        # ކަމަށް + އެވެ -> ކަމަށެވެ
    if word.endswith("އި"):
        return word[:-1] + EVE_ENDING        # ގައި + އެވެ -> ގައެވެ
    return word + EVE                         # ކުރި + އެވެ -> ކުރިއެވެ


def _issue(rule: str, severity: str, message: str, start: int, end: int,
           replacement: Optional[str] = None) -> Dict:
    d = {"rule": rule, "severity": severity, "message": message,
         "start": start, "end": end}
    if replacement is not None:
        d["replacement"] = replacement
    return d


class GrammarChecker:
    def check(self, text: str) -> List[Dict]:
        issues: List[Dict] = []
        tokens = tokenize(text)
        issues += self._punctuation(text)
        issues += self._spacing(text)
        issues += self._repeated_words(text, tokens)
        issues += self._detached_eve(text, tokens)
        issues += self._register_and_length(text)
        issues.sort(key=lambda d: (d["start"], d["end"]))
        return issues

    # -- character-level rules -----------------------------------------

    def _punctuation(self, text: str) -> List[Dict]:
        issues = []
        for latin, thaana, rule, msg in _PUNCT_MAP:
            for i, ch in enumerate(text):
                if ch != latin:
                    continue
                # only flag when the preceding non-space char is Thaana;
                # the span absorbs preceding spaces so the fix is clean
                j = i - 1
                while j >= 0 and text[j] == " ":
                    j -= 1
                if j >= 0 and 0x0780 <= ord(text[j]) <= 0x07B1:
                    issues.append(_issue(rule, "error", msg, j + 1, i + 1, thaana))
        return issues

    def _spacing(self, text: str) -> List[Dict]:
        issues = []
        for m in _SPACE_BEFORE_RE.finditer(text):
            issues.append(_issue(
                "space-before-punct", "error",
                "remove the space before punctuation",
                m.start(), m.end(), m.group(1)))
        for m in _SPACE_AFTER_RE.finditer(text):
            issues.append(_issue(
                "space-after-punct", "warning",
                "add a space after punctuation",
                m.start(), m.end(), m.group(1) + " "))
        for m in _DOUBLE_SPACE_RE.finditer(text):
            issues.append(_issue(
                "double-space", "style",
                "multiple spaces collapsed to one",
                m.start(), m.end(), " "))
        return issues

    # -- token-level rules ------------------------------------------------

    def _repeated_words(self, text: str, tokens) -> List[Dict]:
        issues = []
        for prev, cur in zip(tokens, tokens[1:]):
            if (prev.word == cur.word
                    and text[prev.end:cur.start].strip() == ""):
                issues.append(_issue(
                    "repeated-word", "warning",
                    "the word '%s' is repeated" % prev.word,
                    prev.start, cur.end, prev.word))
        return issues

    def _detached_eve(self, text: str, tokens) -> List[Dict]:
        issues = []
        for prev, cur in zip(tokens, tokens[1:]):
            if (cur.word == EVE and prev.word != EVE
                    and text[prev.end:cur.start].strip() == ""
                    and text[prev.end:cur.start] != ""):
                issues.append(_issue(
                    "detached-eve", "error",
                    "the sentence-final particle eve must be attached: "
                    "%s + %s -> %s" % (prev.word, EVE, merge_eve(prev.word)),
                    prev.start, cur.end, merge_eve(prev.word)))
        return issues

    # -- sentence-level rules ---------------------------------------------

    def _register_and_length(self, text: str) -> List[Dict]:
        issues = []
        sentences = []
        for m in _SENTENCE_RE.finditer(text):
            stoks = tokenize(m.group())
            if not stoks:
                continue
            last = stoks[-1]
            sentences.append({
                "tokens": stoks,
                "offset": m.start(),
                "last": last,
                "formal": last.word.endswith(EVE_ENDING),
            })
            if len(stoks) > LONG_SENTENCE_WORDS:
                issues.append(_issue(
                    "long-sentence", "style",
                    "very long sentence (%d words) — consider splitting it"
                    % len(stoks),
                    m.start() + stoks[0].start, m.start() + last.end))

        substantial = [s for s in sentences if len(s["tokens"]) >= 3]
        if len(substantial) >= 3:
            formal = sum(1 for s in substantial if s["formal"])
            if formal / len(substantial) >= 0.6:
                for s in substantial:
                    if not s["formal"]:
                        last = s["last"]
                        issues.append(_issue(
                            "formal-register", "style",
                            "this document uses the formal written register "
                            "(sentences end in -eve), but this sentence does not",
                            s["offset"] + last.start, s["offset"] + last.end))
        return issues

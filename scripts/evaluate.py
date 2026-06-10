"""Measure spell-checker quality with synthetic-but-realistic corruptions.

Usage:  python scripts/evaluate.py [--n 500] [--seed 42]

For each sampled lexicon word, one corruption is applied, drawn from the
error classes real Dhivehi typists make:
  fili-swap        wrong vowel sign (often short<->long)
  confusion        wrong same-sound consonant (Arabic-loan letters)
  delete-unit      a whole consonant+fili unit dropped
  transpose        two adjacent units swapped
  drop-sukun       trailing sukun lost (structure error)

Reported:
  detection rate     corrupted word flagged (not 'ok')
  top-1 / top-5      original word appears first / in first five suggestions
  false positives    clean lexicon words wrongly flagged
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dhivehi_spell.checker import SpellChecker                      # noqa: E402
from dhivehi_spell.thaana import (CONFUSION_SETS, FILI,             # noqa: E402
                                  FILI_LENGTH_PAIRS, SUKUN, parse_units)

PLAIN_FILI = sorted(FILI - {SUKUN})


def corrupt(word: str, rng: random.Random):
    """Return (corrupted_word, error_class) or None if not corruptible."""
    units, errors = parse_units(word)
    if errors or len(units) < 3:
        return None
    kind = rng.choice(["fili-swap", "confusion", "delete-unit",
                       "transpose", "drop-sukun"])
    chars = list(word)

    if kind == "drop-sukun":
        if not word.endswith(SUKUN):
            return None
        return word[:-1], kind

    if kind == "fili-swap":
        idxs = [i for i, ch in enumerate(chars) if ch in FILI and ch != SUKUN]
        if not idxs:
            return None
        i = rng.choice(idxs)
        paired = FILI_LENGTH_PAIRS.get(chars[i])
        chars[i] = paired if paired and rng.random() < 0.6 else \
            rng.choice([f for f in PLAIN_FILI if f != chars[i]])
        return "".join(chars), kind

    if kind == "confusion":
        cands = []
        for i, ch in enumerate(chars):
            for group in CONFUSION_SETS:
                if ch in group and len(group) > 1:
                    cands.append((i, sorted(group - {ch})))
        if not cands:
            return None
        i, options = rng.choice(cands)
        chars[i] = rng.choice(options)
        return "".join(chars), kind

    # unit-level operations need unit boundaries
    spans = []
    pos = 0
    for u in units:
        width = 1 if u.fili is None else 2
        spans.append((pos, pos + width))
        pos += width

    if kind == "delete-unit":
        a, b = spans[rng.randrange(len(spans))]
        return word[:a] + word[b:], kind

    if kind == "transpose":
        i = rng.randrange(len(spans) - 1)
        (a1, b1), (a2, b2) = spans[i], spans[i + 1]
        return word[:a1] + word[a2:b2] + word[a1:b1] + word[b2:], kind

    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-detection", type=float, default=None,
                    help="exit 1 if detection %% falls below this")
    ap.add_argument("--min-top1", type=float, default=None,
                    help="exit 1 if top-1 %% falls below this")
    ap.add_argument("--max-fp", type=float, default=None,
                    help="exit 1 if false-positive %% exceeds this")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    checker = SpellChecker()
    lexicon = checker.lexicon

    # frequency-weighted sample of well-formed words
    pool = [(w, f) for w, f in lexicon.words.items()
            if f >= 3 and not parse_units(w)[1] and len(parse_units(w)[0]) >= 3]
    words = [w for w, _ in pool]
    weights = [f for _, f in pool]

    per_kind = defaultdict(lambda: [0, 0, 0, 0])  # total, detected, top1, top5
    tried = 0
    while tried < args.n:
        word = rng.choices(words, weights)[0]
        result = corrupt(word, rng)
        if result is None:
            continue
        bad, kind = result
        if bad == word or bad in lexicon:
            continue          # corruption produced another real word
        tried += 1
        r = checker.check_word(bad)
        stats = per_kind[kind]
        stats[0] += 1
        if not r.is_correct:
            stats[1] += 1
            sugg = [s for s, _ in r.suggestions]
            if sugg[:1] == [word]:
                stats[2] += 1
            if word in sugg[:5]:
                stats[3] += 1

    # false positives on clean words
    clean = rng.sample(words, min(args.n, len(words)))
    fp = sum(1 for w in clean if not checker.check_word(w).is_correct)

    print("%-12s %7s %10s %7s %7s" % ("class", "n", "detected", "top-1", "top-5"))
    totals = [0, 0, 0, 0]
    for kind in sorted(per_kind):
        n, det, t1, t5 = per_kind[kind]
        totals = [a + b for a, b in zip(totals, per_kind[kind])]
        print("%-12s %7d %9.1f%% %6.1f%% %6.1f%%"
              % (kind, n, 100 * det / n, 100 * t1 / n, 100 * t5 / n))
    n, det, t1, t5 = totals
    print("%-12s %7d %9.1f%% %6.1f%% %6.1f%%"
          % ("TOTAL", n, 100 * det / n, 100 * t1 / n, 100 * t5 / n))
    fp_pct = 100 * fp / len(clean)
    print("false positives on clean words: %d / %d (%.2f%%)"
          % (fp, len(clean), fp_pct))

    failures = []
    if args.min_detection is not None and 100 * det / n < args.min_detection:
        failures.append("detection %.1f%% < %.1f%%"
                        % (100 * det / n, args.min_detection))
    if args.min_top1 is not None and 100 * t1 / n < args.min_top1:
        failures.append("top-1 %.1f%% < %.1f%%" % (100 * t1 / n, args.min_top1))
    if args.max_fp is not None and fp_pct > args.max_fp:
        failures.append("false positives %.2f%% > %.2f%%"
                        % (fp_pct, args.max_fp))
    if failures:
        print("QUALITY GATE FAILED: " + "; ".join(failures))
        sys.exit(1)


if __name__ == "__main__":
    main()

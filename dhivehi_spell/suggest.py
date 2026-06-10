"""Suggestion ranking: weighted Damerau-Levenshtein over Thaana units.

Cost model (per edit), tuned so that common Dhivehi mistakes rank first:
  - short <-> long fili swap (a/aa, i/ee, ...)          0.40
  - other fili substitution, same consonant             0.70
  - consonant from the same confusion set, same fili    0.50  (e.g. seenu/saadhu)
  - unrelated consonant, same fili                      1.00
  - both consonant and fili differ                      capped at 1.50
  - insert or delete a whole unit                       1.00
  - transpose two adjacent units                        0.80
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .thaana import FILI_LENGTH_PAIRS, same_confusion_set

UnitTuple = Tuple[Optional[str], Optional[str]]

INSERT_DELETE_COST = 1.0
TRANSPOSE_COST = 0.8
MAX_SUB_COST = 1.5


def _fili_cost(a: Optional[str], b: Optional[str]) -> float:
    if a == b:
        return 0.0
    if a is not None and FILI_LENGTH_PAIRS.get(a) == b:
        return 0.4
    return 0.7


def _consonant_cost(a: Optional[str], b: Optional[str]) -> float:
    if a == b:
        return 0.0
    if a is not None and b is not None and same_confusion_set(a, b):
        return 0.5
    return 1.0


def substitution_cost(a: UnitTuple, b: UnitTuple) -> float:
    if a == b:
        return 0.0
    return min(_consonant_cost(a[0], b[0]) + _fili_cost(a[1], b[1]), MAX_SUB_COST)


def unit_distance(a: Sequence[UnitTuple], b: Sequence[UnitTuple],
                  max_cost: float) -> float:
    """Damerau-Levenshtein (optimal string alignment) with weighted costs.

    Returns a value > max_cost as soon as the distance provably exceeds it.
    """
    la, lb = len(a), len(b)
    if abs(la - lb) * INSERT_DELETE_COST > max_cost:
        return max_cost + 1.0

    prev2: List[float] = []
    prev = [j * INSERT_DELETE_COST for j in range(lb + 1)]
    for i in range(1, la + 1):
        cur = [i * INSERT_DELETE_COST] + [0.0] * lb
        best_in_row = cur[0]
        for j in range(1, lb + 1):
            cost = min(
                prev[j] + INSERT_DELETE_COST,                  # delete
                cur[j - 1] + INSERT_DELETE_COST,               # insert
                prev[j - 1] + substitution_cost(a[i - 1], b[j - 1]),
            )
            if (i > 1 and j > 1 and a[i - 1] == b[j - 2]
                    and a[i - 2] == b[j - 1] and a[i - 1] != b[j - 1]):
                cost = min(cost, prev2[j - 2] + TRANSPOSE_COST)
            cur[j] = cost
            best_in_row = min(best_in_row, cost)
        if best_in_row > max_cost:
            return max_cost + 1.0
        prev2, prev = prev, cur
    return prev[lb]


def rank_suggestions(query_units: Sequence[UnitTuple],
                     candidates,                # iterable of (word, units, freq)
                     max_cost: float = 2.0,
                     limit: int = 5) -> List[Tuple[str, float]]:
    """Score candidates against the query and return the best (word, cost)."""
    scored = []
    for word, units, freq in candidates:
        d = unit_distance(query_units, units, max_cost)
        if d <= max_cost:
            scored.append((d, -freq, word))
    scored.sort()
    return [(word, round(d, 3)) for d, _nf, word in scored[:limit]]

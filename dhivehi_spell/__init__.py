"""Offline Dhivehi (Thaana) spell checker."""

from .checker import SpellChecker, WordResult
from .thaana import is_well_formed, parse_units, romanize, tokenize

__version__ = "0.1.0"
__all__ = [
    "SpellChecker", "WordResult",
    "tokenize", "parse_units", "is_well_formed", "romanize",
]

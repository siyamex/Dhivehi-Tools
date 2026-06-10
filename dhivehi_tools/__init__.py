"""Dhivehi Tools — offline language tools for Dhivehi (Thaana).

  - spell checking   (dhivehi_spell.SpellChecker, re-exported here)
  - grammar checking (GrammarChecker)
  - paraphrasing     (Paraphraser)
"""

from dhivehi_spell import SpellChecker

from .grammar import GrammarChecker
from .paraphrase import Paraphraser

__version__ = "0.2.0"
__all__ = ["SpellChecker", "GrammarChecker", "Paraphraser"]

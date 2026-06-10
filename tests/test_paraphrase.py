# -*- coding: utf-8 -*-
import unittest

from dhivehi_spell import SpellChecker
from dhivehi_tools.paraphrase import Paraphraser


class TestParaphraser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pp = Paraphraser()

    def test_thesaurus_loaded(self):
        self.assertGreater(len(self.pp.synonyms), 5000)

    def test_known_synonym_pair(self):
        # from Radheef: ހަހަރު is defined as ލޯބި
        self.assertIn("ލޯބި", self.pp.alternatives("ހަހަރު"))
        self.assertIn("ހަހަރު", self.pp.alternatives("ލޯބި"))  # bidirectional

    def test_full_aggressiveness_swaps_swappable_word(self):
        result = self.pp.paraphrase("މީހުން ހަހަރުވެތި", aggressiveness=1.0, seed=1)
        self.assertGreaterEqual(result["swapped"], 1)
        self.assertNotEqual(result["text"], "މީހުން ހަހަރުވެތި")

    def test_zero_aggressiveness_changes_nothing(self):
        text = "މީހުން ހަހަރުވެތި ބައެކެވެ"
        result = self.pp.paraphrase(text, aggressiveness=0.0, seed=1)
        self.assertEqual(result["text"], text)
        self.assertEqual(result["swapped"], 0)
        # swappable words are still reported for the UI
        self.assertGreaterEqual(result["swappable"], 1)

    def test_deterministic_for_same_seed(self):
        text = "މި ރަށުގެ މީހުން ވަރަށް ހަހަރުވެތި ބައެކެވެ"
        a = self.pp.paraphrase(text, 0.8, seed=7)
        b = self.pp.paraphrase(text, 0.8, seed=7)
        self.assertEqual(a["text"], b["text"])

    def test_output_offsets_match_output_text(self):
        text = "މީހުން ހަހަރުވެތި ބައެކެވެ"
        result = self.pp.paraphrase(text, 1.0, seed=3)
        for r in result["replacements"]:
            emitted = result["text"][r["start"]:r["end"]]
            expected = r["used"] if r["used"] else r["original"]
            self.assertEqual(emitted, expected)

    def test_swaps_are_always_real_words(self):
        lexicon = SpellChecker().lexicon
        text = "މި ރަށުގެ މީހުން ވަރަށް ހަހަރުވެތި ބައެކެވެ"
        result = self.pp.paraphrase(text, 1.0, seed=5)
        for r in result["replacements"]:
            if r["used"]:
                self.assertIn(r["used"], lexicon)

    def test_non_thaana_text_untouched(self):
        result = self.pp.paraphrase("hello world 123", 1.0, seed=1)
        self.assertEqual(result["text"], "hello world 123")
        self.assertEqual(result["swappable"], 0)


if __name__ == "__main__":
    unittest.main()

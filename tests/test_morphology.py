# -*- coding: utf-8 -*-
import unittest

from dhivehi_tools.morphology import EVE_RULES, RULES, analyze, generate


class TestGeneration(unittest.TestCase):
    def test_sukun_stem_cases(self):
        forms = generate("ރަށް")
        for f in ("ރަށުގައި", "ރަށުގެ", "ރަށުން", "ރަށަށް", "ރަށެއް",
                  "ރަށަކީ", "ރަށްތައް", "ރަށްތަކުގައި", "ރަށާއި"):
            self.assertIn(f, forms, f)

    def test_s_mutation(self):
        forms = generate("ބަސް")
        for f in ("ބަހުގެ", "ބަހަށް", "ބަހެއް", "ބަސްތައް"):
            self.assertIn(f, forms, f)

    def test_n_mutation(self):
        forms = generate("ނަން")
        for f in ("ނަމުގެ", "ނަމެއް", "ނަމަކީ"):
            self.assertIn(f, forms, f)

    def test_vowel_final_stems(self):
        self.assertIn("ވާހަކައިގެ", generate("ވާހަކަ"))
        self.assertIn("މަގަށް", generate("މަގު"))
        self.assertIn("ދޯނީގައި", generate("ދޯނި"))
        self.assertIn("ގޭގައި", generate("ގެ"))

    def test_eve_rules(self):
        self.assertIn("ކުރިއެވެ", generate("ކުރި", EVE_RULES))
        self.assertIn("ކަމަށެވެ", generate("ކަމަށް", EVE_RULES))


class TestAnalysis(unittest.TestCase):
    def _roundtrip(self, stem):
        known = lambda w: w == stem
        for form in generate(stem):
            self.assertIn(stem, analyze(form, known),
                          "%s did not analyze back to %s" % (form, stem))

    def test_roundtrip_sukun_stem(self):
        self._roundtrip("ރަށް")

    def test_roundtrip_mutating_stems(self):
        self._roundtrip("ބަސް")
        self._roundtrip("ނަން")

    def test_roundtrip_vowel_stems(self):
        for stem in ("ވާހަކަ", "މަގު", "ދޯނި", "ގެ", "ފަޅޯ"):
            self._roundtrip(stem)

    def test_eve_stacked_on_case(self):
        # ރަށުގައެވެ -> (de-eve) ރަށުގައި -> (case) ރަށް
        self.assertIn("ރަށް", analyze("ރަށުގައެވެ", lambda w: w == "ރަށް"))

    def test_checker_uses_morphology(self):
        from dhivehi_spell import SpellChecker
        checker = SpellChecker()
        # a stacked rare form unlikely to be a corpus headword
        result = checker.check_word("ފަންސުރުތަކަކަށް")
        self.assertTrue(result.is_correct)


class TestVerbMorphology(unittest.TestCase):
    def test_kurun_class_generation(self):
        from dhivehi_tools.morphology import VERB_RULES
        forms = generate("ކުރުން", VERB_RULES)
        for f in ("ކުރަނީ", "ކުރަން", "ކުރި", "ކުރީ", "ކުރާ", "ކުރާނެ",
                  "ކުރޭ", "ކުރަމުން", "ކުރެވޭ", "ކުރެވުނު"):
            self.assertIn(f, forms, f)

    def test_verb_analysis_roundtrip(self):
        from dhivehi_tools.morphology import VERB_RULES
        for lemma in ("ކުރުން", "ބުނުން", "ލިޔުން"):
            known = lambda w: w == lemma
            for form in generate(lemma, VERB_RULES):
                self.assertIn(lemma, analyze(form, known),
                              "%s !-> %s" % (form, lemma))

    def test_verb_form_with_eve(self):
        # ކުރެވުނެވެ -> (de-eve) ކުރެވުނު? No: ކުރެވުނ+ެވެ... covered form:
        # ބުނާނެއެވެ -> ބުނާނެ -> ބުނުން
        self.assertIn("ބުނުން",
                      analyze("ބުނާނެއެވެ", lambda w: w == "ބުނުން"))

    def test_checker_accepts_conjugation(self):
        from dhivehi_spell import SpellChecker
        checker = SpellChecker(wordlist=None)
        checker.lexicon.add("ދެއްކުން", 10)   # to show / display
        result = checker.check_word("ދެއްކަމުން")
        self.assertTrue(result.is_correct)
        self.assertEqual(result.via, "ދެއްކުން")


class TestRealWordErrors(unittest.TestCase):
    def test_context_flag_with_suggestion(self):
        from dhivehi_spell import SpellChecker
        checker = SpellChecker()
        if not checker.bigrams:
            self.skipTest("no bigram data")
        # 'boadu' (board) after 'enme' should suggest 'bodu' (big)
        issues = checker.check_text("އެންމެ ބޯޑު")
        ctx = [d for d in issues if d["status"] == "context"]
        self.assertEqual(len(ctx), 1)
        self.assertEqual(ctx[0]["suggestions"][0]["word"], "ބޮޑު")

    def test_supported_word_not_flagged(self):
        from dhivehi_spell import SpellChecker
        checker = SpellChecker()
        issues = checker.check_text("އެންމެ ބޮޑު")
        self.assertEqual([d for d in issues if d["status"] == "context"], [])

    def test_real_word_check_can_be_disabled(self):
        from dhivehi_spell import SpellChecker
        checker = SpellChecker()
        issues = checker.check_text("އެންމެ ބޯޑު", real_word_check=False)
        self.assertEqual(issues, [])


class TestRuleTableSanity(unittest.TestCase):
    def test_rules_are_unique(self):
        self.assertEqual(len(RULES), len(set(RULES)))

    def test_no_identity_rules(self):
        for remove, append in RULES + EVE_RULES:
            self.assertNotEqual(remove, append)


if __name__ == "__main__":
    unittest.main()

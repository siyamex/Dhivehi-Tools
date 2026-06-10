# -*- coding: utf-8 -*-
import unittest

from dhivehi_spell import SpellChecker, is_well_formed, parse_units, tokenize
from dhivehi_spell.checker import SpellChecker as _SC


class TestThaanaStructure(unittest.TestCase):
    def test_simple_valid_word(self):
        self.assertTrue(is_well_formed("ދިވެހި"))          # dhivehi

    def test_sukun_initial_loanword(self):
        self.assertTrue(is_well_formed("ސްކޫލް"))          # skool (school)

    def test_prenasalized_noonu_is_valid(self):
        # kan'du, han'dhu, an'ga: bare noonu before voiced stop
        for w in ("ކަނޑު", "ހަނދު", "އަނގަ", "ކުރުނބާ"):
            self.assertTrue(is_well_formed(w), w)

    def test_bare_consonant_is_invalid(self):
        units, errors = parse_units("ދިވެހ")               # final haa missing fili
        self.assertEqual(errors[0].code, "missing-fili")

    def test_bare_noonu_not_before_voiced_stop_is_invalid(self):
        _, errors = parse_units("ކަނތު")                   # noonu before thaa: needs sukun
        self.assertTrue(any(e.code == "missing-fili" for e in errors))

    def test_orphan_fili_is_invalid(self):
        _, errors = parse_units("ަދިވެހި")                 # leading stray abafili
        self.assertEqual(errors[0].code, "orphan-fili")

    def test_tokenize_extracts_thaana_runs(self):
        toks = tokenize("hello ދިވެހި 123 ރާއްޖެ!")
        self.assertEqual([t.word for t in toks], ["ދިވެހި", "ރާއްޖެ"])


class TestLexiconIntegrity(unittest.TestCase):
    def test_every_seed_word_is_well_formed(self):
        from dhivehi_spell.dictionary import DEFAULT_WORDLIST, Lexicon
        seed = Lexicon()
        seed.load(DEFAULT_WORDLIST)
        bad = [w for w in seed.iter_words() if not is_well_formed(w)]
        self.assertEqual(bad, [], "malformed seed words: %r" % bad)

    def test_full_lexicon_mostly_well_formed(self):
        # Radheef contains a handful of archaic/dialectal spellings that are
        # kept as exact-match entries; they must stay a tiny minority.
        lex = SpellChecker().lexicon
        irregular = sum(1 for w in lex.iter_words() if not is_well_formed(w))
        self.assertLess(irregular / len(lex), 0.01)

    def test_radheef_lexicon_loaded(self):
        checker = SpellChecker()
        self.assertGreater(len(checker.lexicon), 30000)
        # a Radheef word that is not in the seed list
        self.assertEqual(checker.check_word("ހަހަރުވެތި").status, "ok")

    def test_irregular_official_spelling_accepted(self):
        # bare noonu outside prenasalization, but an official Radheef entry
        checker = SpellChecker()
        self.assertEqual(checker.check_word("ހީނލުން").status, "ok")


class TestChecking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = SpellChecker()

    def test_known_word_ok(self):
        self.assertEqual(self.checker.check_word("ރާއްޖެ").status, "ok")

    def test_unknown_word_flagged(self):
        # 'raajja' (wrong final fili) is not a word
        self.assertEqual(self.checker.check_word("ރާއްޖަ").status, "unknown")

    def test_suggestion_for_wrong_fili(self):
        result = self.checker.check_word("ރާއްޖަ")
        self.assertEqual(result.suggestions[0][0], "ރާއްޖެ")

    def test_suggestion_for_confusable_consonant(self):
        # 'shukuriyyaa' spelled with seenu instead of sheenu
        result = self.checker.check_word("ސުކުރިއްޔާ")
        words = [w for w, _ in result.suggestions]
        self.assertIn("ޝުކުރިއްޔާ", words)

    def test_suffixed_form_accepted_via_stem(self):
        # rashugai = rah (island) + locative -gai with u-sandhi.
        # Use a minimal checker: the full corpus contains the form directly.
        checker = _SC(wordlist=None)
        checker.lexicon.add("ރަށް", 10)
        result = checker.check_word("ރަށުގައި")
        self.assertEqual(result.status, "ok-derived")
        self.assertEqual(result.via, "ރަށް")

    def test_indefinite_suffix_with_fili_fusion(self):
        # fotheh = foiy (book) + -eh; suffix consumed the stem's sukun
        checker = _SC(wordlist=None)
        checker.lexicon.add("ފޮތް", 10)
        result = checker.check_word("ފޮތެއް")
        self.assertEqual(result.status, "ok-derived")
        self.assertEqual(result.via, "ފޮތް")

    def test_structure_error_reported_with_suggestions(self):
        result = self.checker.check_word("ދިވެހ")
        self.assertEqual(result.status, "structure")
        words = [w for w, _ in result.suggestions]
        self.assertIn("ދިވެހި", words)

    def test_check_text_offsets(self):
        text = "އަހަރެން ދިވެހ ބަސް"
        issues = self.checker.check_text(text)
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(text[issue["start"]:issue["end"]], "ދިވެހ")

    def test_clean_text_has_no_issues(self):
        self.assertEqual(self.checker.check_text("އަހަރެން ވަރަށް ލޯބި"), [])

    def test_add_words_runtime(self):
        checker = _SC()
        word = "ޓުޒިފޮގެޕު"  # nonsense, but structurally valid
        self.assertFalse(checker.check_word(word).is_correct)
        checker.add_words([word])
        self.assertTrue(checker.check_word(word).is_correct)


if __name__ == "__main__":
    unittest.main()

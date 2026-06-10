# -*- coding: utf-8 -*-
import unittest

from dhivehi_tools.grammar import GrammarChecker, merge_eve


def rules(issues):
    return [i["rule"] for i in issues]


class TestMergeEve(unittest.TestCase):
    def test_vowel_final_concatenates(self):
        self.assertEqual(merge_eve("ކުރި"), "ކުރިއެވެ")

    def test_sukun_final_fuses(self):
        self.assertEqual(merge_eve("ކަމަށް"), "ކަމަށެވެ")

    def test_ai_final_contracts(self):
        self.assertEqual(merge_eve("ދޯނީގައި"), "ދޯނީގައެވެ")


class TestGrammarRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gc = GrammarChecker()

    def test_clean_text(self):
        self.assertEqual(self.gc.check("އަހަރެން މާލެ ދިޔައީމެވެ."), [])

    def test_latin_comma_flagged_with_replacement(self):
        issues = self.gc.check("ރީތި , އުފާވެރި")
        comma = [i for i in issues if i["rule"] == "thaana-comma"]
        self.assertEqual(len(comma), 1)
        self.assertEqual(comma[0]["replacement"], "،")

    def test_latin_comma_in_latin_context_ignored(self):
        self.assertNotIn("thaana-comma", rules(self.gc.check("hello, world")))

    def test_space_before_punct(self):
        issues = self.gc.check("ދިޔައީމެވެ ،")
        self.assertIn("space-before-punct", rules(issues))

    def test_space_after_punct(self):
        issues = self.gc.check("ދިޔައީމެވެ.އަދި")
        hit = [i for i in issues if i["rule"] == "space-after-punct"]
        self.assertEqual(hit[0]["replacement"], ". ")

    def test_double_space(self):
        self.assertIn("double-space", rules(self.gc.check("އެއް  ދެ")))

    def test_repeated_word(self):
        text = "ވަރަށް ވަރަށް ރީތި"
        issues = [i for i in self.gc.check(text) if i["rule"] == "repeated-word"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(text[issues[0]["start"]:issues[0]["end"]],
                         "ވަރަށް ވަރަށް")
        self.assertEqual(issues[0]["replacement"], "ވަރަށް")

    def test_detached_eve(self):
        text = "ދިޔައީ ދޯނީގައި އެވެ."
        issues = [i for i in self.gc.check(text) if i["rule"] == "detached-eve"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["replacement"], "ދޯނީގައެވެ")

    def test_formal_register_inconsistency(self):
        text = ("އަހަރެން މާލެ ދިޔައީމެވެ. މޫސުން ވަރަށް ރަނގަޅެވެ. "
                "ދަތުރު ވަރަށް އުފާވެރިއެވެ. އެކަމަކު ކަނޑު ވަރަށް ގަދަ.")
        issues = [i for i in self.gc.check(text) if i["rule"] == "formal-register"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(text[issues[0]["start"]:issues[0]["end"]], "ގަދަ")

    def test_no_register_flag_for_informal_document(self):
        text = "މިއަދު މޫސުން ރަނގަޅު. ކަނޑު މަޑު. ދަތުރު އުފާވެރި."
        self.assertNotIn("formal-register", rules(self.gc.check(text)))

    def test_replacements_splice_cleanly(self):
        text = "ދިޔައީ ދޯނީގައި އެވެ. ރީތި , އުފާވެރި  ދުވަހެއް"
        issues = self.gc.check(text)
        fixable = [i for i in issues if "replacement" in i]
        self.assertTrue(fixable)
        # apply right-to-left so earlier offsets stay valid
        for it in sorted(fixable, key=lambda d: -d["start"]):
            text = text[:it["start"]] + it["replacement"] + text[it["end"]:]
        remaining = [i for i in self.gc.check(text) if "replacement" in i]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()

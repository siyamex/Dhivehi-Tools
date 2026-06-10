# -*- coding: utf-8 -*-
import unittest

from dhivehi_tools.transform import to_formal, to_informal
from dhivehi_tools.translit import latin_to_thaana, thaana_to_latin


class TestTranslit(unittest.TestCase):
    def test_latin_to_thaana_basic(self):
        self.assertEqual(latin_to_thaana("dhivehi"), "ދިވެހި")
        self.assertEqual(latin_to_thaana("maale"), "މާލެ")

    def test_long_vowels_and_digraphs(self):
        self.assertEqual(latin_to_thaana("dhoani"), "ދޯނި")
        self.assertEqual(latin_to_thaana("loabi"), "ލޯބި")

    def test_final_consonant_gets_sukun(self):
        self.assertEqual(latin_to_thaana("fas"), "ފަސް")
        self.assertEqual(latin_to_thaana("rah"), "ރަށް")
        self.assertEqual(latin_to_thaana("varah reethi"), "ވަރަށް ރީތި")

    def test_prenasal_apostrophe(self):
        self.assertEqual(latin_to_thaana("kan'du"), "ކަނޑު")

    def test_vowel_initial_rides_alifu(self):
        self.assertEqual(latin_to_thaana("ufaa"), "އުފާ")

    def test_thaana_to_latin(self):
        self.assertEqual(thaana_to_latin("ދިވެހި"), "dhivehi")
        self.assertEqual(thaana_to_latin("މާލެ"), "maale")

    def test_non_letters_pass_through(self):
        self.assertEqual(latin_to_thaana("123 !"), "123 !")


class TestRegister(unittest.TestCase):
    def test_to_formal_attaches_eve(self):
        self.assertEqual(to_formal("މޫސުން ވަރަށް ރީތި."),
                         "މޫސުން ވަރަށް ރީތިއެވެ.")

    def test_to_formal_sukun_fusion(self):
        self.assertEqual(to_formal("ދިޔައީ މާލެއަށް."),
                         "ދިޔައީ މާލެއަށެވެ.")

    def test_to_formal_idempotent(self):
        text = "މޫސުން ރީތިއެވެ."
        self.assertEqual(to_formal(text), text)

    def test_to_informal_strips_eve(self):
        self.assertEqual(to_informal("މޫސުން ވަރަށް ރީތިއެވެ."),
                         "މޫސުން ވަރަށް ރީތި.")
        self.assertEqual(to_informal("ދިޔައީ މާލެއަށެވެ."),
                         "ދިޔައީ މާލެއަށް.")

    def test_to_informal_first_person(self):
        self.assertEqual(to_informal("އަހަރެން ދިޔައީމެވެ."),
                         "އަހަރެން ދިޔައީ.")

    def test_multiple_sentences(self):
        text = "މޫސުން ރީތި. ކަނޑު މަޑު."
        formal = to_formal(text)
        self.assertEqual(formal, "މޫސުން ރީތިއެވެ. ކަނޑު މަޑުއެވެ.")
        self.assertEqual(to_informal(formal), text)


if __name__ == "__main__":
    unittest.main()

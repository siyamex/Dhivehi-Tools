# -*- coding: utf-8 -*-
import json
import threading
import unittest
from http.client import HTTPConnection

from dhivehi_tools.web import create_server


class TestToolsWebAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _post(self, path, body):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        conn.request("POST", path, payload, {"Content-Type": "application/json"})
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()
        return res.status, data

    def _get(self, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        conn.close()
        return res.status, raw

    def test_index_is_tabbed_ui(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("Dhivehi Tools", body)
        self.assertIn("Paraphrase", body)

    def test_stats_includes_synonyms(self):
        status, raw = self._get("/api/stats")
        data = json.loads(raw)
        self.assertGreater(data["words"], 30000)
        self.assertGreater(data["synonyms"], 5000)

    def test_spell_endpoint(self):
        status, data = self._post("/api/spell/check", {"text": "ދިވެހ"})
        self.assertEqual(status, 200)
        self.assertEqual(data["issues"][0]["status"], "structure")

    def test_grammar_endpoint(self):
        status, data = self._post("/api/grammar/check",
                                  {"text": "ދިޔައީ ދޯނީގައި އެވެ."})
        self.assertEqual(status, 200)
        rules = [i["rule"] for i in data["issues"]]
        self.assertIn("detached-eve", rules)

    def test_paraphrase_endpoint(self):
        status, data = self._post("/api/paraphrase",
                                  {"text": "މީހުން ހަހަރުވެތި",
                                   "aggressiveness": 1.0, "seed": 2})
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["swapped"], 1)

    def test_paraphrase_bad_params(self):
        status, _ = self._post("/api/paraphrase",
                               {"text": "x", "aggressiveness": "lots"})
        self.assertEqual(status, 400)

    def test_define_endpoint(self):
        status, data = self._post("/api/define", {"q": "ހަހަރު"})
        self.assertEqual(status, 200)
        self.assertTrue(data["definitions"])

    def test_translit_endpoints(self):
        status, data = self._post("/api/translit",
                                  {"text": "dhivehi", "to": "thaana"})
        self.assertEqual(data["text"], "ދިވެހި")
        status, data = self._post("/api/translit",
                                  {"text": "ދިވެހި", "to": "latin"})
        self.assertEqual(data["text"], "dhivehi")

    def test_register_endpoint(self):
        status, data = self._post("/api/register",
                                  {"text": "މޫސުން ރީތި.", "target": "formal"})
        self.assertEqual(data["text"], "މޫސުން ރީތިއެވެ.")

    def test_unknown_logging(self):
        word = "ޕިޒޮގުޓެ"  # nonsense, structurally valid
        self._post("/api/spell/check", {"text": word})
        status, raw = self._get("/api/unknowns")
        words = [u["word"] for u in json.loads(raw)["unknowns"]]
        self.assertIn(word, words)

    def test_reverse_dictionary(self):
        # ހަހަރު is defined as ލޯބި, so a reverse search for ލޯބި finds it
        status, data = self._post("/api/reverse", {"q": "ލޯބި"})
        self.assertEqual(status, 200)
        words = [r["word"] for r in data["results"]]
        self.assertIn("ހަހަރު", words)

    def test_dhivehi_js_served(self):
        status, body = self._get("/dhivehi.js")
        self.assertEqual(status, 200)
        self.assertIn("latinToThaana", body)

    def test_pwa_assets_served(self):
        status, body = self._get("/manifest.json")
        self.assertEqual(status, 200)
        self.assertIn("Dhivehi Tools", body)
        status, body = self._get("/sw.js")
        self.assertEqual(status, 200)
        self.assertIn("dhivehi-tools-v", body)
        status, _ = self._get("/icon.svg")
        self.assertEqual(status, 200)

    def test_font_served(self):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/fonts/mvtyper.ttf")
        res = conn.getresponse()
        raw = res.read()
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertEqual(res.getheader("Content-Type"), "font/ttf")
        self.assertGreater(len(raw), 50000)

    def test_languagetool_protocol(self):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        body = "text=" + __import__("urllib.parse", fromlist=["quote"]).quote(
            "ދިވެހ ބަސް") + "&language=dv"
        conn.request("POST", "/v2/check", body.encode("utf-8"),
                     {"Content-Type": "application/x-www-form-urlencoded"})
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        conn.close()
        self.assertEqual(res.status, 200)
        self.assertEqual(data["language"]["code"], "dv")
        self.assertTrue(data["matches"])
        m = data["matches"][0]
        self.assertEqual(m["offset"], 0)
        self.assertEqual(m["length"], 5)
        self.assertTrue(m["replacements"])


if __name__ == "__main__":
    unittest.main()

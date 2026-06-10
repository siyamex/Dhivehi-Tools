# -*- coding: utf-8 -*-
import json
import threading
import unittest
from http.client import HTTPConnection

from dhivehi_spell.web import create_server


class TestWebAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)            # ephemeral port
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, method, path, body=None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None
        headers = {"Content-Type": "application/json"} if payload else {}
        conn.request(method, path, payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()
        return res.status, data

    def test_index_served(self):
        status, body = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Dhivehi Spell Checker", body)

    def test_stats(self):
        status, body = self._request("GET", "/api/stats")
        self.assertEqual(status, 200)
        self.assertGreater(json.loads(body)["words"], 150)

    def test_check_endpoint_reports_issue_with_offsets(self):
        text = "އަހަރެން ދިވެހ ބަސް"
        status, body = self._request("POST", "/api/check", {"text": text})
        self.assertEqual(status, 200)
        issues = json.loads(body)["issues"]
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue["status"], "structure")
        self.assertEqual(text[issue["start"]:issue["end"]], "ދިވެހ")
        self.assertEqual(issue["suggestions"][0]["word"], "ދިވެހި")

    def test_word_endpoint(self):
        status, body = self._request("POST", "/api/word", {"word": "ރާއްޖެ"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_add_endpoint_extends_lexicon(self):
        word = "ޒިފޮގެޕުޓު"  # nonsense, but structurally valid
        status, body = self._request("POST", "/api/check", {"text": word})
        self.assertEqual(len(json.loads(body)["issues"]), 1)
        status, body = self._request("POST", "/api/add", {"words": [word]})
        self.assertEqual(status, 200)
        status, body = self._request("POST", "/api/check", {"text": word})
        self.assertEqual(json.loads(body)["issues"], [])

    def test_cors_preflight_and_headers(self):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("OPTIONS", "/api/check")
        res = conn.getresponse()
        self.assertEqual(res.status, 204)
        self.assertEqual(res.getheader("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", res.getheader("Access-Control-Allow-Methods", ""))
        res.read()
        conn.close()
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/stats")
        res = conn.getresponse()
        self.assertEqual(res.getheader("Access-Control-Allow-Origin"), "*")
        res.read()
        conn.close()

    def test_bad_json_rejected(self):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/check", b"not json",
                     {"Content-Type": "application/json"})
        res = conn.getresponse()
        self.assertEqual(res.status, 400)
        conn.close()


if __name__ == "__main__":
    unittest.main()

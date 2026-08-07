from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import rhine_lore.server as server  # noqa: E402
from rhine_lore.engine import EvolutionStore  # noqa: E402


CHARACTERS = [
    {"id": "hero", "title": "林澈", "content": "想要查明父亲失踪的真相"},
    {"id": "rival", "title": "沈砚", "content": "目标是继承家族商会"},
]
WORLD = [
    {"id": "w1", "title": "雾港", "content": "常年被海雾笼罩的港口城市"},
    {"id": "w2", "title": "沈家商会", "content": "控制着雾港一半的贸易"},
]


class EvolutionApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.original_store = server.EVOLUTION_STORE
        server.EVOLUTION_STORE = EvolutionStore(Path(cls.tempdir.name))
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.RhineLoreHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        server.EVOLUTION_STORE = cls.original_store
        cls.tempdir.cleanup()

    def setUp(self) -> None:
        for path in Path(self.tempdir.name).glob("*.evolution.json"):
            path.unlink()

    def _request(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            return exc.code, json.loads(raw) if raw else {}

    def _start(self, project_id: str = "story-1") -> dict:
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/start",
            {
                "project_id": project_id,
                "project_name": "雾港来信",
                "genre": "悬疑",
                "characters": CHARACTERS,
                "world": WORLD,
                "seed": 42,
                "settings": {"chaos": 50, "branch_frequency": 30, "events_per_turn": 1, "auto_resolve": False},
            },
        )
        self.assertEqual(status, 200)
        return payload

    def test_start_advance_and_novel_view(self) -> None:
        payload = self._start()
        self.assertEqual(payload["state"]["turn"], 0)
        self.assertEqual(len(payload["viewpoints"]), 2)

        status, payload = self._request(
            "POST",
            "/lore-api/evolution/advance",
            {"project_id": "story-1", "choice_id": None, "viewpoint_id": "hero"},
        )
        self.assertEqual(status, 200)
        self.assertIn(payload["state"]["turn"], {1, 0})
        self.assertIsInstance(payload["novel"], dict)
        self.assertEqual(payload["novel"]["viewpoint_id"], "hero")

    def test_branch_can_be_resolved_with_fate(self) -> None:
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/start",
            {
                "project_id": "story-branch",
                "project_name": "雾港来信",
                "genre": "悬疑",
                "characters": CHARACTERS,
                "world": WORLD,
                "seed": 42,
                "settings": {"chaos": 50, "branch_frequency": 100, "events_per_turn": 1, "auto_resolve": False},
            },
        )
        self.assertEqual(status, 200)
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/advance",
            {"project_id": "story-branch", "choice_id": "fate", "viewpoint_id": "hero"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["result"]["awaiting_branch"])
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/advance",
            {"project_id": "story-branch", "choice_id": "fate", "viewpoint_id": "hero"},
        )
        self.assertEqual(status, 200)
        self.assertGreater(len(payload["state"]["history"]), 0)

    def test_missing_run_returns_404(self) -> None:
        status, payload = self._request("GET", "/lore-api/evolution/state?project_id=missing")
        self.assertEqual(status, 404)
        self.assertIn("演化尚未开始", payload["error"])

    def test_ai_prose_requires_api_key(self) -> None:
        self._start("story-ai")
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/ai-prose",
            {"project_id": "story-ai", "viewpoint_id": "hero", "llm": {"api_key": ""}},
        )
        self.assertEqual(status, 400)
        self.assertIn("API Key", payload["error"])

    def test_guide_sets_guidance(self) -> None:
        self._start("story-guide")
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/guide",
            {"project_id": "story-guide", "guidance": "让沈砚背叛林澈"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"]["guidance"], "让沈砚背叛林澈")
        status, payload = self._request("GET", "/lore-api/evolution/state?project_id=story-guide")
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"]["guidance"], "让沈砚背叛林澈")

    def test_add_character_to_run_api(self) -> None:
        payload = self._start("story-addchar")
        self.assertEqual(len(payload["state"]["cast"]), 2)
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/add-character",
            {"project_id": "story-addchar", "character": {"name": "阿岚", "role": "盟友"}, "viewpoint_id": "hero"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["state"]["cast"]), 3)
        status, payload = self._request(
            "POST",
            "/lore-api/evolution/add-character",
            {"project_id": "story-addchar", "character": {}},
        )
        self.assertEqual(status, 400)

    def test_reset_deletes_run(self) -> None:
        self._start()
        status, _ = self._request("POST", "/lore-api/evolution/reset", {"project_id": "story-1"})
        self.assertEqual(status, 200)
        status, _ = self._request("GET", "/lore-api/evolution/state?project_id=story-1")
        self.assertEqual(status, 404)

    def test_chinese_project_id_roundtrip(self) -> None:
        self._start("我的故事")
        quoted = urllib.parse.quote("我的故事")
        status, payload = self._request("GET", f"/lore-api/evolution/state?project_id={quoted}")
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"]["project_id"], "我的故事")


if __name__ == "__main__":
    unittest.main()

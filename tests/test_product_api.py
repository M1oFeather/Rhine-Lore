from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import rhine_lore.server as server  # noqa: E402
from rhine_lore.engine import EvolutionStore  # noqa: E402
from rhine_lore.long_novel_analysis import AnalysisTaskManager  # noqa: E402
from rhine_lore.novel_store import BookStore  # noqa: E402
from rhine_lore.version_store import VersionStore  # noqa: E402


def _story_project(project_id: str = "product-story") -> dict:
    return {
        "id": project_id,
        "name": "雾港来信",
        "genre": "悬疑",
        "summary": "一封来自失踪者的信改变了港口的清晨。",
        "global_guidance": "保持克制的第一人称叙事。",
        "chapter_turns": 4,
        "writing_style": "冷静、清晰",
        "polish_writing": True,
        "style_example": "",
        "style_notes": "",
        "style_avoid": "",
        "world": [],
        "characters": [],
        "map": {"nodes": [], "edges": []},
        "chapters": [{"id": "chapter-1", "title": "第一章", "content": "雾还没有散。"}],
        "chat": [],
        "issues": [],
    }


class ProductApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.data_root = Path(cls.tempdir.name)
        cls.originals = {
            "DATA_ROOT": server.DATA_ROOT,
            "PROJECTS_DIR": server.PROJECTS_DIR,
            "EVOLUTION_STORE": server.EVOLUTION_STORE,
            "BOOK_STORE": server.BOOK_STORE,
            "ANALYSIS_MANAGER": server.ANALYSIS_MANAGER,
            "VERSION_STORE": server.VERSION_STORE,
            "LLM_CONFIG_PATH": server.LLM_CONFIG_PATH,
            "DEFAULT_VAULT_DATABASE": server.DEFAULT_VAULT_DATABASE,
            "_EMBEDDED_VAULT": server._EMBEDDED_VAULT,
        }
        server.DATA_ROOT = cls.data_root
        server.PROJECTS_DIR = cls.data_root / "projects"
        server.EVOLUTION_STORE = EvolutionStore(server.PROJECTS_DIR)
        server.BOOK_STORE = BookStore(cls.data_root)
        server.ANALYSIS_MANAGER = AnalysisTaskManager()
        server.VERSION_STORE = VersionStore(cls.data_root)
        server.LLM_CONFIG_PATH = cls.data_root / "llm-config.json"
        server.DEFAULT_VAULT_DATABASE = cls.data_root / "rhine-vault-core.db"
        server._EMBEDDED_VAULT = None

        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.RhineLoreHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()
        for name, value in cls.originals.items():
            setattr(server, name, value)
        cls.tempdir.cleanup()

    def setUp(self) -> None:
        for child in self.data_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        server.EVOLUTION_STORE.directory.mkdir(parents=True, exist_ok=True)
        server.BOOK_STORE.books_dir.mkdir(parents=True, exist_ok=True)
        server.VERSION_STORE.root.mkdir(parents=True, exist_ok=True)
        server._EMBEDDED_VAULT = None

    def _request(
        self,
        method: str,
        path: str,
        body: dict | bytes | None = None,
        content_type: str = "application/json",
    ) -> tuple[int, dict | bytes, dict[str, str]]:
        if isinstance(body, dict):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        else:
            data = body
        headers = {"Content-Type": content_type} if data is not None else {}
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read()
                response_headers = dict(response.headers.items())
                if response.headers.get_content_type() == "application/json":
                    return response.status, json.loads(raw.decode("utf-8")), response_headers
                return response.status, raw, response_headers
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload: dict | bytes = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = raw
            return exc.code, payload, dict(exc.headers.items())

    def test_project_agent_snapshot_restore_and_missing_errors(self) -> None:
        project = _story_project()
        status, payload, _ = self._request(
            "POST", f"/lore-api/projects/{project['id']}", project
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])

        status, payload, _ = self._request("GET", "/lore-api/projects")
        self.assertEqual(status, 200)
        self.assertEqual(payload["projects"][0]["chapter_count"], 1)

        status, payload, _ = self._request(
            "POST",
            "/lore-api/agent/execute",
            {
                "tool": "append_chapter",
                "args": {
                    "project_id": project["id"],
                    "title": "第二章",
                    "content": "潮声盖过了脚步。",
                },
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["result"]["project"]["chapters"]), 2)
        snapshot_id = payload["snapshot"]["snapshot_id"]

        status, payload, _ = self._request(
            "POST",
            "/lore-api/versions/restore",
            {"kind": "project", "entity_id": project["id"], "snapshot_id": snapshot_id},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["payload"]["chapters"]), 1)

        status, payload, _ = self._request(
            "POST",
            "/lore-api/versions/restore",
            {"kind": "project", "entity_id": project["id"], "snapshot_id": "missing"},
        )
        self.assertEqual(status, 404)
        self.assertIn("快照不存在", payload["error"])

        status, payload, _ = self._request(
            "POST", "/lore-api/agent/execute", {"tool": "list_projects", "args": {}}
        )
        self.assertEqual(status, 400)
        self.assertIn("写操作", payload["error"])

    def test_book_lifecycle_versions_and_backup_include_chapter_text(self) -> None:
        text = "第一章 雾信\n雾还没有散。\n\n第二章 潮汐\n潮声盖过了脚步。"
        status, book, _ = self._request(
            "POST",
            "/lore-api/books/import",
            {
                "name": "雾港来信",
                "genre": "悬疑",
                "text": text,
                "source_encoding": "gb18030",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(book["chapter_count"], 2)
        self.assertEqual(book["source_encoding"], "gb18030")
        book_id = book["book_id"]
        first_id = book["chapters"][0]["id"]

        status, payload, _ = self._request("GET", "/lore-api/books")
        self.assertEqual(status, 200)
        imported = next(row for row in payload["books"] if row["book_id"] == book_id)
        self.assertEqual(imported["source_encoding"], "gb18030")

        revised = "雾还没有散，码头的钟敲了六下。"
        status, payload, _ = self._request(
            "POST",
            f"/lore-api/books/{book_id}/chapters/{first_id}",
            {"title": "第一章 雾信", "content": revised},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["chapter"]["content"], revised)

        status, payload, _ = self._request(
            "POST",
            f"/lore-api/books/{book_id}/ai/write",
            {"chapter_id": first_id, "mode": "continue"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["offline"])

        status, payload, _ = self._request(
            "GET", f"/lore-api/books/{book_id}/analysis/preview?mode=smart"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["plan"]["chapter_count"], book["chapter_count"])

        status, payload, _ = self._request(
            "POST", f"/lore-api/books/{book_id}/analysis/jobs", {"mode": "smart"}
        )
        self.assertEqual(status, 202)
        self.assertTrue(payload["status"]["offline"])
        for _ in range(50):
            status, payload, _ = self._request(
                "GET", f"/lore-api/books/{book_id}/analysis/status"
            )
            if payload["status"]["state"] == "completed":
                break
            time.sleep(0.02)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"]["state"], "completed")
        self.assertIn("基础索引", payload["status"]["message"])

        status, payload, _ = self._request(
            "POST",
            f"/lore-api/books/{book_id}/branches",
            {
                "chapter_id": first_id,
                "offset": 1,
                "anchor": "雾还没有散",
                "guidance": "让港口突然停电",
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["offline"])
        branch = payload["branch"]
        branch_id = branch["branch_id"]
        self.assertEqual(branch["offset"], len("雾还没有散"))
        self.assertEqual(branch["depth"], 0)

        status, payload, _ = self._request(
            "GET", f"/lore-api/books/{book_id}/branches?chapter_id={first_id}"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["branches"][0]["branch_id"], branch_id)

        status, payload, _ = self._request(
            "POST",
            f"/lore-api/books/{book_id}/branches",
            {
                "chapter_id": first_id,
                "offset": len(branch["text"]),
                "guidance": "让陌生人递来另一封信",
                "parent_branch_id": branch_id,
                "kind": "clue",
            },
        )
        self.assertEqual(status, 200)
        child_id = payload["branch"]["branch_id"]
        self.assertEqual(payload["branch"]["parent_branch_id"], branch_id)
        self.assertEqual(payload["branch"]["depth"], 1)

        status, payload, _ = self._request(
            "GET", f"/lore-api/books/{book_id}/branches/{child_id}/path"
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            [item["branch_id"] for item in payload["path"]["lineage"]],
            [branch_id, child_id],
        )

        status, payload, _ = self._request(
            "POST",
            f"/lore-api/books/{book_id}/workbench",
            {"branch_id": branch_id},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["project"]["source_book_id"], book_id)
        self.assertEqual(payload["project"]["source_branch_id"], branch_id)
        self.assertEqual(payload["imported"]["chapters"], 1)
        self.assertTrue(
            (self.data_root / "projects" / f"{payload['project']['id']}.project.json").is_file()
        )

        status, payload, _ = self._request(
            "DELETE", f"/lore-api/books/{book_id}/branches/{child_id}"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["deleted"]["count"], 1)

        status, payload, _ = self._request(
            "POST",
            "/lore-api/versions/commit",
            {"kind": "book", "entity_id": book_id, "message": "合并前"},
        )
        self.assertEqual(status, 200)
        snapshot_id = payload["snapshot"]["snapshot_id"]

        status, payload, _ = self._request(
            "POST",
            "/lore-api/agent/execute",
            {
                "tool": "merge_chapters",
                "args": {"book_id": book_id, "start_order": 1, "end_order": 2},
            },
        )
        self.assertEqual(status, 200)
        merged = payload["result"]["book"]
        self.assertEqual(merged["chapter_count"], 1)
        metadata = json.loads(
            (self.data_root / "books" / book_id / "book.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(metadata["summaries"]), {merged["chapters"][0]["id"]})

        status, payload, _ = self._request(
            "POST",
            "/lore-api/versions/restore",
            {"kind": "book", "entity_id": book_id, "snapshot_id": snapshot_id},
        )
        self.assertEqual(status, 200)
        restored = payload["payload"]["book"]
        self.assertEqual(restored["chapter_count"], 2)
        metadata = json.loads(
            (self.data_root / "books" / book_id / "book.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(metadata["summaries"]), {row["id"] for row in restored["chapters"]})

        status, backup, headers = self._request("POST", "/lore-api/backup/export")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(backup)) as archive:
            names = archive.namelist()
            self.assertTrue(any(name.endswith(f"chapters/{first_id}.txt") for name in names))

        status, _, _ = self._request("DELETE", f"/lore-api/books/{book_id}")
        self.assertEqual(status, 200)
        status, payload, _ = self._request(
            "POST", "/lore-api/backup/import", backup, "application/zip"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["books"], 1)
        status, payload, _ = self._request(
            "GET", f"/lore-api/books/{book_id}/chapters/{first_id}"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["chapter"]["content"], revised)

        status, _, _ = self._request("DELETE", f"/lore-api/books/{book_id}")
        self.assertEqual(status, 200)
        status, payload, _ = self._request("DELETE", f"/lore-api/books/{book_id}")
        self.assertEqual(status, 404)
        self.assertIn("书籍不存在", payload["error"])

    def test_invalid_backup_is_rejected_before_any_file_is_written(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "meta.json",
                json.dumps({"format": "rhine-lore-backup-v1"}),
            )
            archive.writestr(
                "projects/partial.project.json",
                json.dumps({"format": "rhine-lore-project-v1", "project": _story_project()}),
            )
            archive.writestr("books/broken/book.json", "{not-json")

        status, payload, _ = self._request(
            "POST", "/lore-api/backup/import", buffer.getvalue(), "application/zip"
        )
        self.assertEqual(status, 400)
        self.assertIn("导入失败", payload["error"])
        self.assertFalse((self.data_root / "projects" / "partial.project.json").exists())

    def test_conversation_knowledge_extraction_has_offline_review_candidates(self) -> None:
        status, payload, _ = self._request(
            "POST",
            "/lore-api/knowledge/extract",
            {
                "project": {"id": "story-1", "name": "龙娘纪事", "genre": "奇幻"},
                "chapter": {"id": "chapter-1", "title": "觉醒"},
                "messages": [
                    {
                        "id": "message-user",
                        "role": "user",
                        "content": "规则：只有龙娘能够闻到同类觉醒后的气息。",
                    },
                    {
                        "id": "message-assistant",
                        "role": "assistant",
                        "content": "伏笔：林薇一直隐藏自己见过龙角的秘密。",
                    },
                    {
                        "id": "message-template",
                        "role": "assistant",
                        "content": "《第一章》续写草稿\n\n他已经走到门边。\n\n本轮请求：继续写。",
                    },
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["offline"])
        self.assertGreaterEqual(len(payload["candidates"]), 2)
        self.assertEqual(
            {row["node_type"] for row in payload["candidates"]},
            {"Rule", "Foreshadowing"},
        )
        self.assertEqual(payload["candidates"][0]["authority"], "experimental")
        self.assertIn("message-user", payload["candidates"][0]["source_message_ids"])
        self.assertFalse(payload["candidates"][0]["title"].startswith("规则：规则："))

        status, error, _ = self._request(
            "POST",
            "/lore-api/knowledge/extract",
            {"messages": []},
        )
        self.assertEqual(status, 400)
        self.assertIn("至少选择", error["error"])

    def test_embedded_knowledge_intake_review_search_and_backup(self) -> None:
        previous_embedded = os.environ.get("RHINE_LORE_EMBEDDED")
        os.environ["RHINE_LORE_EMBEDDED"] = "1"
        try:
            status, health, _ = self._request("GET", "/api/health")
            self.assertEqual(status, 200)
            self.assertEqual(health["status"], "ok")

            status, proposal, _ = self._request(
                "POST",
                "/api/manual",
                {
                    "workspace_id": "story-workspace",
                    "title": "龙娘觉醒规则",
                    "node_type": "Rule",
                    "content": "龙娘觉醒后会长出角，只有同类能够闻到彼此的气息。",
                    "authority": "experimental",
                    "tags": ["lore", "龙娘"],
                },
            )
            self.assertEqual(status, 200)
            temporary_id = proposal["proposed_nodes"][0]["temporary_id"]

            status, updated, _ = self._request(
                "PATCH",
                f"/api/proposals/{proposal['proposal_id']}/nodes/{temporary_id}",
                {
                    "workspace_id": "story-workspace",
                    "patch": {
                        "title": "龙娘觉醒约束",
                        "node_type": "Rule",
                        "content": "觉醒后会长出角；同类可以闻到觉醒后的气息。",
                        "authority": "experimental",
                        "tags": ["lore", "规则"],
                    },
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(updated["proposed_nodes"][0]["title"], "龙娘觉醒约束")

            status, staging, _ = self._request(
                "POST",
                f"/api/proposals/{proposal['proposal_id']}/stage",
                {"workspace_id": "story-workspace", "temporary_ids": [temporary_id]},
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(staging), 1)

            status, approved, _ = self._request(
                "POST",
                "/api/staging/approve",
                {"workspace_id": "story-workspace", "entry_ids": [staging[0]["entry_id"]]},
            )
            self.assertEqual(status, 200)
            self.assertEqual(approved[0]["status"], "approved")

            status, nodes, _ = self._request(
                "GET", "/api/nodes?workspace_id=story-workspace"
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(nodes), 1)
            self.assertEqual(nodes[0]["revision"], 1)
            approved_node_id = nodes[0]["node_id"]

            status, replacement, _ = self._request(
                "POST",
                "/api/manual",
                {
                    "workspace_id": "story-workspace",
                    "title": "龙娘觉醒约束补充",
                    "node_type": "Rule",
                    "content": "觉醒气息只会持续七天。",
                    "authority": "approved",
                    "tags": ["lore", "规则", "覆盖"],
                },
            )
            self.assertEqual(status, 200)
            replacement_temporary_id = replacement["proposed_nodes"][0]["temporary_id"]
            status, _, _ = self._request(
                "PATCH",
                f"/api/proposals/{replacement['proposal_id']}/nodes/{replacement_temporary_id}",
                {
                    "workspace_id": "story-workspace",
                    "patch": {"node_id": approved_node_id},
                },
            )
            self.assertEqual(status, 200)
            status, replacement_staging, _ = self._request(
                "POST",
                f"/api/proposals/{replacement['proposal_id']}/stage",
                {
                    "workspace_id": "story-workspace",
                    "temporary_ids": [replacement_temporary_id],
                },
            )
            self.assertEqual(status, 200)
            replacement_entry = next(
                item for item in replacement_staging
                if item["proposal_id"] == replacement["proposal_id"]
            )
            self.assertEqual(replacement_entry["base_revision"], 1)
            status, _, _ = self._request(
                "POST",
                "/api/staging/approve",
                {
                    "workspace_id": "story-workspace",
                    "entry_ids": [replacement_entry["entry_id"]],
                },
            )
            self.assertEqual(status, 200)

            status, nodes, _ = self._request(
                "GET", "/api/nodes?workspace_id=story-workspace"
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(nodes), 1)
            self.assertEqual(nodes[0]["revision"], 2)
            self.assertEqual(nodes[0]["content"], "觉醒气息只会持续七天。")

            status, revisions, _ = self._request(
                "GET",
                f"/api/nodes/{approved_node_id}/revisions?workspace_id=story-workspace",
            )
            self.assertEqual(status, 200)
            self.assertEqual([item["revision"] for item in revisions], [1, 2])
            status, rolled_back, _ = self._request(
                "POST",
                f"/api/nodes/{approved_node_id}/rollback",
                {"workspace_id": "story-workspace", "revision": 1},
            )
            self.assertEqual(status, 200)
            self.assertEqual(rolled_back["revision"], 3)
            self.assertIn("同类可以闻到", rolled_back["content"])

            status, context, _ = self._request(
                "POST",
                "/api/context",
                {
                    "workspace_id": "story-workspace",
                    "query": "觉醒 龙娘",
                    "tags": ["lore"],
                    "result_limit": 6,
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(context["results"]), 1)
            self.assertIn("龙娘觉醒约束", context["context"])

            status, document, _ = self._request(
                "POST",
                "/api/documents/generate",
                {
                    "workspace_id": "story-workspace",
                    "query": "龙娘",
                    "tags": ["lore"],
                    "title": "故事设定集",
                },
            )
            self.assertEqual(status, 200)
            self.assertIn("# 故事设定集", document["markdown"])

            database = sqlite3.connect(server.DEFAULT_VAULT_DATABASE)
            try:
                database.execute("CREATE TABLE backup_probe (value TEXT NOT NULL)")
                database.execute("INSERT INTO backup_probe VALUES ('core-ready')")
                database.commit()
            finally:
                database.close()

            status, backup, _ = self._request("POST", "/lore-api/backup/export")
            self.assertEqual(status, 200)
            with zipfile.ZipFile(io.BytesIO(backup)) as archive:
                self.assertIn("embedded-vault.json", archive.namelist())
                self.assertIn("rhine-vault-core.db", archive.namelist())

            (self.data_root / "embedded-vault.json").unlink()
            server.DEFAULT_VAULT_DATABASE.unlink()
            server._EMBEDDED_VAULT = None
            status, restored, _ = self._request(
                "POST", "/lore-api/backup/import", backup, "application/zip"
            )
            self.assertEqual(status, 200)
            self.assertEqual(restored["knowledge"], 2)

            status, nodes, _ = self._request(
                "GET", "/api/nodes?workspace_id=story-workspace"
            )
            self.assertEqual(status, 200)
            self.assertEqual(nodes[0]["title"], "龙娘觉醒约束")
            database = sqlite3.connect(server.DEFAULT_VAULT_DATABASE)
            try:
                value = database.execute("SELECT value FROM backup_probe").fetchone()[0]
            finally:
                database.close()
            self.assertEqual(value, "core-ready")

            status, rejected_draft, _ = self._request(
                "POST",
                "/api/manual",
                {
                    "workspace_id": "story-workspace",
                    "title": "待丢弃设定",
                    "node_type": "Note",
                    "content": "这条资料不应进入正式知识库。",
                    "authority": "experimental",
                    "tags": ["lore"],
                },
            )
            self.assertEqual(status, 200)
            status, rejected, _ = self._request(
                "POST",
                f"/api/proposals/{rejected_draft['proposal_id']}/reject",
                {"workspace_id": "story-workspace"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(rejected["status"], "rejected")
        finally:
            if previous_embedded is None:
                os.environ.pop("RHINE_LORE_EMBEDDED", None)
            else:
                os.environ["RHINE_LORE_EMBEDDED"] = previous_embedded
            server._EMBEDDED_VAULT = None


if __name__ == "__main__":
    unittest.main()

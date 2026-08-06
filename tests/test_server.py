from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rhine_lore.server import (
    DEFAULT_VAULT_DATABASE,
    DEFAULT_VAULT_PORT,
    DEFAULT_VAULT_PORT_CANDIDATES,
    _coerce_local_host,
    _coerce_port,
    _default_vault_config,
    _is_allowed_vault_url,
    _join_base_and_path,
    _resolve_vault_checkout,
    _vault_web_status,
    proxy_url,
)


class ProxySafetyTests(unittest.TestCase):
    def test_allows_local_vault_urls(self) -> None:
        self.assertTrue(_is_allowed_vault_url("http://127.0.0.1:8765"))
        self.assertTrue(_is_allowed_vault_url("http://localhost:8765"))

    def test_rejects_non_local_vault_urls(self) -> None:
        self.assertFalse(_is_allowed_vault_url("https://example.com"))
        self.assertFalse(_is_allowed_vault_url("file:///tmp/rhine-vault.db"))

    def test_proxy_path_must_be_api_scoped(self) -> None:
        with self.assertRaises(ValueError):
            _join_base_and_path("http://127.0.0.1:8765", "/admin")

    def test_proxy_path_preserves_query_string(self) -> None:
        self.assertEqual(
            _join_base_and_path("http://127.0.0.1:8765", "/api/nodes?workspace_id=story"),
            "http://127.0.0.1:8765/api/nodes?workspace_id=story",
        )

    def test_proxy_url_encodes_query_values(self) -> None:
        self.assertIn("base_url=http%3A%2F%2F127.0.0.1%3A8765", proxy_url("http://127.0.0.1:8765", "/api/health"))

    def test_vault_launcher_rejects_remote_host(self) -> None:
        with self.assertRaises(ValueError):
            _coerce_local_host("0.0.0.0")

    def test_vault_launcher_validates_port(self) -> None:
        self.assertEqual(_coerce_port("8765"), 8765)
        with self.assertRaises(ValueError):
            _coerce_port("70000")

    def test_vault_checkout_must_contain_main_py(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            path = Path(raw_dir)
            with self.assertRaises(ValueError):
                _resolve_vault_checkout(path)
            (path / "main.py").write_text("", encoding="utf-8")
            self.assertEqual(_resolve_vault_checkout(path), path.resolve())

    def test_default_vault_config_uses_lore_data_database(self) -> None:
        self.assertEqual(_default_vault_config()["database_path"], str(DEFAULT_VAULT_DATABASE))
        self.assertEqual(_default_vault_config()["port"], DEFAULT_VAULT_PORT)

    def test_default_vault_port_avoids_blender_conflict(self) -> None:
        self.assertEqual(DEFAULT_VAULT_PORT, 8795)
        self.assertNotIn(8765, DEFAULT_VAULT_PORT_CANDIDATES)
        self.assertEqual(DEFAULT_VAULT_PORT_CANDIDATES[0], DEFAULT_VAULT_PORT)

    def test_vault_web_status_detects_installable_ui(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            path = Path(raw_dir)
            (path / "main.py").write_text("", encoding="utf-8")
            (path / "ui").mkdir()
            (path / "ui" / "package.json").write_text("{}", encoding="utf-8")

            status = _vault_web_status(path, "http://127.0.0.1:8765")

            self.assertTrue(status["installable"])
            self.assertFalse(status["installed"])
            self.assertEqual(status["url"], "http://127.0.0.1:8765/")

    def test_vault_web_status_detects_built_ui(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            path = Path(raw_dir)
            (path / "main.py").write_text("", encoding="utf-8")
            (path / "ui" / "dist").mkdir(parents=True)
            (path / "ui" / "dist" / "index.html").write_text("", encoding="utf-8")

            status = _vault_web_status(path, "http://127.0.0.1:8765")

            self.assertTrue(status["installed"])
            self.assertIn("ui", status["web_root"])


if __name__ == "__main__":
    unittest.main()

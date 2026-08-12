"""Small static server with a local Rhine-Vault proxy and launcher."""

from __future__ import annotations

import json
import copy
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from rhine_lore.embedded_vault import EmbeddedVaultStore
from rhine_lore.engine import (
    EvolutionState,
    EvolutionStore,
    QUALITY_GUIDE,
    TurnResult,
    add_character_to_run,
    advance,
    build_ai_prose_prompt,
    evolution_settings_from_dict,
    evolution_state_to_dict,
    needs_new_character,
    render_novel,
    render_sandbox,
    sanitize_project_id,
    start_run,
    suggested_character,
    turn_result_to_dict,
    viewpoint_options,
)
from rhine_lore.novel_store import BookStore, _heuristic_summary
from rhine_lore.version_store import VersionStore


ALLOWED_PROXY_HOSTS = {"127.0.0.1", "localhost", "::1"}
ALLOWED_METHODS = {"GET", "POST", "PATCH"}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get("RHINE_LORE_DATA_DIR") or (PROJECT_ROOT / "data"))
PROJECTS_DIR = DATA_ROOT / "projects"
PROJECT_BACKUP_FORMAT = "rhine-lore-project-v1"
LLM_CONFIG_PATH = DATA_ROOT / "llm-config.json"
DEFAULT_VAULT_HOST = "127.0.0.1"
DEFAULT_VAULT_PORT = 8795
DEFAULT_VAULT_PORT_CANDIDATES = (8795, 8796, 8797)
DEFAULT_VAULT_PORTS = set(DEFAULT_VAULT_PORT_CANDIDATES)
DEFAULT_VAULT_URL = f"http://{DEFAULT_VAULT_HOST}:{DEFAULT_VAULT_PORT}"
DEFAULT_VAULT_CHECKOUT = Path(__file__).resolve().parents[3] / "Rhine-Vault"
DEFAULT_VAULT_DATABASE = PROJECT_ROOT / "data" / "rhine-vault-core.db"
VAULT_WEB_INSTALL_TIMEOUT = 300
EVOLUTION_STORE = EvolutionStore(PROJECTS_DIR)
BOOK_STORE = BookStore(DATA_ROOT)
VERSION_STORE = VersionStore(DATA_ROOT)


def _is_embedded() -> bool:
    return os.environ.get("RHINE_LORE_EMBEDDED") == "1"


_EMBEDDED_VAULT: EmbeddedVaultStore | None = None
_EMBEDDED_VAULT_LOCK = threading.Lock()


def _embedded_vault() -> EmbeddedVaultStore:
    global _EMBEDDED_VAULT
    if _EMBEDDED_VAULT is None:
        with _EMBEDDED_VAULT_LOCK:
            if _EMBEDDED_VAULT is None:
                _EMBEDDED_VAULT = EmbeddedVaultStore(DATA_ROOT)
    return _EMBEDDED_VAULT


class VaultProcessManager:
    def __init__(self) -> None:
        self.process: subprocess.Popen[bytes] | None = None
        self.command: list[str] = []
        self.vault_path: Path | None = None
        self.base_url = os.environ.get("RHINE_LORE_VAULT_URL", DEFAULT_VAULT_URL).strip() or DEFAULT_VAULT_URL
        self.auto_start_attempted = False
        self.auto_start_error = ""

    def status(self) -> dict[str, Any]:
        running = self.process is not None and self.process.poll() is None
        self.base_url = os.environ.get("RHINE_LORE_VAULT_URL", self.base_url).strip() or DEFAULT_VAULT_URL
        parsed_base = urlparse(self.base_url)
        is_external = parsed_base.port not in DEFAULT_VAULT_PORTS
        return {
            "managed": self.process is not None,
            "running": running,
            "pid": self.process.pid if running and self.process else None,
            "returncode": None if running or self.process is None else self.process.returncode,
            "base_url": self.base_url,
            "vault_path": str(self.vault_path) if self.vault_path else "",
            "command": self.command,
            "mode": "external" if is_external else "default-core",
            "auto_start": {
                "enabled": _vault_autostart_enabled(),
                "attempted": self.auto_start_attempted,
                "error": self.auto_start_error,
            },
        }

    def connect(self, base_url: str) -> dict[str, Any]:
        if not _is_allowed_vault_url(base_url):
            raise ValueError("base_url must point to localhost, 127.0.0.1, or ::1")
        self.base_url = base_url.rstrip("/")
        os.environ["RHINE_LORE_VAULT_URL"] = self.base_url
        return self.status()

    def start(
        self,
        *,
        vault_path: Path,
        host: str,
        port: int,
        database_path: Path | None,
        python_path: Path | None,
    ) -> dict[str, Any]:
        if self.process is not None and self.process.poll() is None:
            return self.status()
        resolved_vault_path = _resolve_vault_checkout(vault_path)
        interpreter = _resolve_python_interpreter(resolved_vault_path, python_path)
        command = [
            str(interpreter),
            "main.py",
            "server",
            "--host",
            host,
            "--port",
            str(port),
        ]
        if database_path is not None:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            command.extend(["--database", str(database_path)])

        env = os.environ.copy()
        env["RHINE_VAULT_HOST"] = host
        env["RHINE_VAULT_PORT"] = str(port)
        if database_path is not None:
            env["RHINE_VAULT_DB"] = str(database_path)

        err_file = tempfile.NamedTemporaryFile(mode="w+b", suffix=".log", delete=False)
        try:
            self.process = subprocess.Popen(
                command,
                cwd=resolved_vault_path,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=err_file,
            )
            self.command = command
            self.vault_path = resolved_vault_path
        except OSError:
            err_file.close()
            raise
        if not self._wait_healthy(port, timeout=6):
            self.auto_start_error = self._failure_detail(err_file)
            err_file.close()
            self._remove_log(err_file.name)
            return self.status()
        err_file.close()
        self._remove_log(err_file.name)
        self.connect(f"http://{host}:{port}")
        self.auto_start_error = ""
        return self.status()

    def _wait_healthy(self, port: int, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                return False
            if _vault_health(f"http://{DEFAULT_VAULT_HOST}:{port}").get("connected"):
                return True
            time.sleep(0.4)
        return bool(_vault_health(f"http://{DEFAULT_VAULT_HOST}:{port}").get("connected"))

    def _failure_detail(self, err_file: tempfile._TemporaryFileWrapper[bytes] | None) -> str:
        pieces: list[str] = []
        code = self.process.poll() if self.process is not None else None
        if code is not None:
            pieces.append(f"进程退出 code={code}")
        tail = ""
        if err_file is not None:
            try:
                err_file.flush()
                err_file.seek(0)
                tail = err_file.read()[-1500:].decode("utf-8", errors="replace")
            except OSError:
                pass
        if tail.strip():
            last_line = tail.strip().splitlines()[-1]
            pieces.append(last_line[:300])
        return "；".join(pieces) or "端口未响应健康检查"

    @staticmethod
    def _remove_log(name: str) -> None:
        try:
            Path(name).unlink(missing_ok=True)
        except OSError:
            pass

    def ensure_default_core(self) -> dict[str, Any]:
        self.auto_start_attempted = True
        if not _vault_autostart_enabled():
            return self.status()
        if self.process is not None and self.process.poll() is None:
            return self.status()
        configured_url = os.environ.get("RHINE_LORE_VAULT_URL", "").strip().rstrip("/")
        if configured_url and configured_url != DEFAULT_VAULT_URL:
            self.connect(configured_url)
            return self.status()
        errors: list[str] = []
        for port in DEFAULT_VAULT_PORT_CANDIDATES:
            candidate_url = f"http://{DEFAULT_VAULT_HOST}:{port}"
            if _vault_health(candidate_url).get("connected"):
                self.connect(candidate_url)
                self.auto_start_error = ""
                return self.status()
            try:
                started = self.start(
                    vault_path=DEFAULT_VAULT_CHECKOUT,
                    host=DEFAULT_VAULT_HOST,
                    port=port,
                    database_path=DEFAULT_VAULT_DATABASE,
                    python_path=None,
                )
            except (OSError, ValueError) as exc:
                errors.append(f"{port}: {exc}")
                continue
            if started["running"] and _vault_health(f"http://{DEFAULT_VAULT_HOST}:{port}").get("connected"):
                return started
            errors.append(f"{port}: {started['auto_start']['error'] or '启动后未通过健康检查'}")
        self.auto_start_error = "；".join(errors) or "未找到可用的 Vault 端口"
        return self.status()

    def stop(self) -> dict[str, Any]:
        if self.process is None:
            return self.status()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=8)
        return self.status()


VAULT_MANAGER = VaultProcessManager()


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _is_allowed_vault_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in ALLOWED_PROXY_HOSTS


def _join_base_and_path(base_url: str, api_path: str) -> str:
    if not api_path.startswith("/api/"):
        raise ValueError("proxy path must start with /api/")
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("base_url must be an absolute HTTP URL")
    target = urlparse(api_path)
    return urlunparse((parsed.scheme, parsed.netloc, target.path, "", target.query, ""))


def _coerce_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("port must be an integer") from exc
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    return port


def _coerce_local_host(value: Any) -> str:
    host = str(value or "127.0.0.1").strip()
    if host not in ALLOWED_PROXY_HOSTS:
        raise ValueError("host must be localhost, 127.0.0.1, or ::1")
    return host


def _vault_autostart_enabled() -> bool:
    if os.environ.get("RHINE_LORE_EMBEDDED") == "1":
        return False
    raw = os.environ.get("RHINE_LORE_DISABLE_VAULT_AUTOSTART", "").strip().lower()
    return raw not in {"1", "true", "yes", "on"}


def _resolve_vault_checkout(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"vault_path does not exist: {resolved}")
    if not (resolved / "main.py").is_file():
        raise ValueError("vault_path must point to a Rhine-Vault checkout containing main.py")
    return resolved


def _resolve_python_interpreter(vault_path: Path, python_path: Path | None = None) -> Path:
    if python_path is not None:
        resolved = python_path.expanduser().resolve()
        if not resolved.is_file():
            raise ValueError(f"python_path does not exist: {resolved}")
        return resolved
    venv_python = vault_path / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return venv_python
    return Path(sys.executable)


def _default_vault_config() -> dict[str, Any]:
    return {
        "vault_path": str(DEFAULT_VAULT_CHECKOUT),
        "host": DEFAULT_VAULT_HOST,
        "port": DEFAULT_VAULT_PORT,
        "database_path": str(DEFAULT_VAULT_DATABASE),
        "python_path": "",
        "base_url": os.environ.get("RHINE_LORE_VAULT_URL", DEFAULT_VAULT_URL).strip() or DEFAULT_VAULT_URL,
    }


def _npm_command() -> str:
    return os.environ.get("RHINE_LORE_NPM", "npm.cmd" if os.name == "nt" else "npm")


def _tail_output(value: str, limit: int = 4000) -> str:
    return value[-limit:] if len(value) > limit else value


def _timeout_output(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return _tail_output(value.decode("utf-8", errors="replace"))
    return _tail_output(str(value or ""))


def _vault_web_status(vault_path: Path | None = None, base_url: str | None = None) -> dict[str, Any]:
    raw_path = vault_path or DEFAULT_VAULT_CHECKOUT
    try:
        resolved = _resolve_vault_checkout(raw_path)
    except ValueError as exc:
        return {
            "vault_path": str(raw_path),
            "installed": False,
            "installable": False,
            "url": (base_url or DEFAULT_VAULT_URL).rstrip("/") + "/",
            "web_root": "",
            "package_dir": "",
            "install_command": [],
            "error": str(exc),
        }

    ui_dir = resolved / "ui"
    dist_index = ui_dir / "dist" / "index.html"
    legacy_web_index = resolved / "web" / "index.html"
    web_root = dist_index.parent if dist_index.is_file() else legacy_web_index.parent if legacy_web_index.is_file() else ui_dir / "dist"
    package_dir = ui_dir if (ui_dir / "package.json").is_file() else None
    npm = _npm_command()
    return {
        "vault_path": str(resolved),
        "installed": dist_index.is_file() or legacy_web_index.is_file(),
        "installable": package_dir is not None,
        "url": (base_url or DEFAULT_VAULT_URL).rstrip("/") + "/",
        "web_root": str(web_root),
        "package_dir": str(package_dir or ""),
        "install_command": [npm, "install", "&&", npm, "run", "build"] if package_dir else [],
        "error": "",
    }


def _install_vault_web(vault_path: Path | None = None) -> dict[str, Any]:
    resolved = _resolve_vault_checkout(vault_path or DEFAULT_VAULT_CHECKOUT)
    ui_dir = resolved / "ui"
    if not (ui_dir / "package.json").is_file():
        raise ValueError("Vault Web install requires a Rhine-Vault ui/package.json")
    npm = _npm_command()
    install = subprocess.run(
        [npm, "install"],
        cwd=ui_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=VAULT_WEB_INSTALL_TIMEOUT,
    )
    build = subprocess.run(
        [npm, "run", "build"],
        cwd=ui_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=VAULT_WEB_INSTALL_TIMEOUT,
    )
    status = _vault_web_status(resolved, VAULT_MANAGER.status()["base_url"])
    status["install"] = {
        "install_stdout": _tail_output(install.stdout),
        "install_stderr": _tail_output(install.stderr),
        "build_stdout": _tail_output(build.stdout),
        "build_stderr": _tail_output(build.stderr),
    }
    return status


def _vault_health(base_url: str) -> dict[str, Any]:
    if not _is_allowed_vault_url(base_url):
        return {"connected": False, "error": "base_url must be local"}
    try:
        with urlopen(_join_base_and_path(base_url, "/api/health"), timeout=2) as response:
            raw = response.read()
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            return {"connected": True, "health": payload}
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"connected": False, "error": str(exc)}


def _evolution_payload(
    state: EvolutionState,
    result: TurnResult | None = None,
    viewpoint_id: str = "",
) -> dict[str, Any]:
    viewpoint = viewpoint_id or (state.cast[0].id if state.cast else "")
    wants_character = needs_new_character(state)
    return {
        "state": evolution_state_to_dict(state),
        "sandbox": render_sandbox(state),
        "novel": render_novel(state, viewpoint),
        "viewpoints": viewpoint_options(state),
        "result": turn_result_to_dict(result) if result else None,
        "message": result.message if result else "",
        "needs_character": wants_character,
        "suggested_character": suggested_character(state) if wants_character else None,
    }


def _load_llm_config() -> dict[str, str]:
    if LLM_CONFIG_PATH.is_file():
        try:
            data = json.loads(LLM_CONFIG_PATH.read_text(encoding="utf-8"))
            return {
                "base_url": str(data.get("base_url") or "").strip(),
                "api_key": str(data.get("api_key") or "").strip(),
                "model": str(data.get("model") or "").strip(),
                "preset": str(data.get("preset") or "deepseek").strip(),
            }
        except (OSError, json.JSONDecodeError):
            pass
    return {"base_url": "", "api_key": "", "model": "", "preset": "deepseek"}


def _save_llm_config(config: dict[str, str]) -> None:
    LLM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = LLM_CONFIG_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, LLM_CONFIG_PATH)


def _mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 6:
        return "••••"
    return f"{api_key[:3]}••••{api_key[-3:]}"


def _llm_config_payload(config: dict[str, str]) -> dict[str, Any]:
    return {
        "configured": bool(config.get("api_key")),
        "base_url": config.get("base_url") or "",
        "model": config.get("model") or "",
        "preset": config.get("preset") or "deepseek",
        "masked_key": _mask_key(config.get("api_key") or ""),
    }


def _offline_ai_write(mode: str) -> str:
    if mode == "rewrite":
        return (
            "（离线模板·改写）请先在首页配置 AI 通道，即可对本章进行 AI 改写。\n\n"
            "当前未配置 API Key，正文保持原样。"
        )
    if mode == "expand":
        return (
            "（离线模板·扩写）请先在首页配置 AI 通道，即可对本章进行 AI 扩写。\n\n"
            "当前未配置 API Key，正文保持原样。"
        )
    return (
        "（离线模板·续写）请先在首页配置 AI 通道，即可在章末续写下一段。\n\n"
        "当前未配置 API Key，正文保持原样。"
    )


def _agent_project_path(project_id: str) -> Path:
    return EVOLUTION_STORE.directory / f"{sanitize_project_id(project_id)}.project.json"


def _new_agent_project(name: str, genre: str, summary: str) -> dict[str, Any]:
    project_id = f"project-{uuid.uuid4().hex[:10]}"
    return {
        "id": project_id,
        "name": name.strip() or "新故事",
        "genre": genre.strip() or "未分类",
        "summary": summary.strip(),
        "global_guidance": "",
        "chapter_turns": 4,
        "writing_style": "",
        "polish_writing": True,
        "style_example": "",
        "style_notes": "",
        "style_avoid": "",
        "world": [],
        "characters": [],
        "map": {"nodes": [], "edges": []},
        "chapters": [],
        "chat": [],
        "issues": [],
    }


def _load_agent_project(project_id: str) -> dict[str, Any]:
    path = _agent_project_path(project_id)
    if not path.is_file():
        raise KeyError(f"项目不存在: {project_id}")
    backup = json.loads(path.read_text(encoding="utf-8"))
    project = backup.get("project") or {}
    if not project:
        raise KeyError("项目数据损坏")
    return project


def _save_agent_project(project: dict[str, Any]) -> dict[str, Any]:
    project_id = str(project.get("id") or "").strip()
    if not project_id:
        raise ValueError("project id 不能为空")
    path = _agent_project_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"format": PROJECT_BACKUP_FORMAT, "project": project}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return project


def _list_agent_projects() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    store_dir = EVOLUTION_STORE.directory
    if store_dir.is_dir():
        for path in sorted(store_dir.glob("*.project.json")):
            try:
                backup = json.loads(path.read_text(encoding="utf-8"))
                project = backup.get("project") or {}
                rows.append(
                    {
                        "project_id": str(project.get("id") or ""),
                        "name": str(project.get("name") or "未命名"),
                        "genre": str(project.get("genre") or "未分类"),
                        "chapter_count": len(project.get("chapters") or []),
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
    return rows


def _list_projects_meta() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    store_dir = EVOLUTION_STORE.directory
    if store_dir.is_dir():
        for path in sorted(store_dir.glob("*.project.json")):
            try:
                backup = json.loads(path.read_text(encoding="utf-8"))
                project = backup.get("project") or {}
                rows.append(
                    {
                        "project_id": str(project.get("id") or ""),
                        "name": str(project.get("name") or "未命名"),
                        "genre": str(project.get("genre") or "未分类"),
                        "summary": str(project.get("summary") or ""),
                        "chapter_count": len(project.get("chapters") or []),
                        "world_count": len(project.get("world") or []),
                        "character_count": len(project.get("characters") or []),
                        "total_chars": _project_char_count(project),
                        "updated_at": time.strftime(
                            "%Y-%m-%dT%H:%M:%S%z",
                            time.localtime(path.stat().st_mtime),
                        ),
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
    return rows


def _evolution_summary(state: EvolutionState) -> dict[str, Any]:
    latest = state.history[-1] if state.history else None
    return {
        "project_id": state.project_id,
        "project_name": state.project_name,
        "turn": state.turn,
        "tension": state.world.tension,
        "latest_event": latest.title if latest else None,
        "awaiting_branch": bool(state.pending_branch),
        "branch_question": state.pending_branch.question if state.pending_branch else None,
        "guidance": state.guidance or "",
    }


def _run_agent_tool(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    if tool == "import_txt":
        return {
            "book": BOOK_STORE.import_txt(
                name=str(args.get("name") or "未命名小说"),
                text=str(args.get("text") or ""),
                genre=str(args.get("genre") or ""),
            )
        }
    if tool == "create_project":
        project = _new_agent_project(
            str(args.get("name") or ""),
            str(args.get("genre") or ""),
            str(args.get("summary") or ""),
        )
        _save_agent_project(project)
        return {"project": project}
    if tool == "append_chapter":
        project = _load_agent_project(str(args.get("project_id") or ""))
        chapters = project.setdefault("chapters", [])
        chapters.append(
            {
                "id": f"ch-{uuid.uuid4().hex[:10]}",
                "title": str(args.get("title") or f"第{len(chapters) + 1}章"),
                "content": str(args.get("content") or ""),
            }
        )
        _save_agent_project(project)
        return {"project": project}
    if tool == "add_character":
        project = _load_agent_project(str(args.get("project_id") or ""))
        characters = project.setdefault("characters", [])
        characters.append(
            {
                "id": f"character-{uuid.uuid4().hex[:10]}",
                "name": str(args.get("name") or "未命名角色"),
                "identity": str(args.get("identity") or ""),
                "role": str(args.get("role") or "配角"),
                "age": str(args.get("age") or ""),
                "stance": str(args.get("stance") or ""),
                "drive": str(args.get("drive") or ""),
                "fear": str(args.get("fear") or ""),
                "traits": str(args.get("traits") or ""),
                "abilities": str(args.get("abilities") or ""),
                "weakness": str(args.get("weakness") or ""),
                "secret": str(args.get("secret") or ""),
                "speech": str(args.get("speech") or ""),
                "appearance": str(args.get("appearance") or ""),
                "background": str(args.get("background") or ""),
                "relationships": [],
                "status": "正常",
                "notes": "",
            }
        )
        _save_agent_project(project)
        return {"project": project}
    if tool == "update_character":
        project = _load_agent_project(str(args.get("project_id") or ""))
        characters = project.setdefault("characters", [])
        target = str(args.get("name") or "").strip()
        target_id = str(args.get("id") or "").strip()
        card = next(
            (
                item
                for item in characters
                if (target_id and item.get("id") == target_id)
                or (target and item.get("name") == target)
            ),
            None,
        )
        if card is None:
            raise KeyError(f"角色不存在: {target or target_id}")
        fields = (
            "identity",
            "role",
            "age",
            "stance",
            "drive",
            "fear",
            "traits",
            "abilities",
            "weakness",
            "secret",
            "speech",
            "appearance",
            "background",
            "status",
            "notes",
        )
        for field in fields:
            if field in args and args[field] is not None:
                card[field] = str(args[field])
        if "relationships" in args and isinstance(args["relationships"], list):
            card["relationships"] = args["relationships"]
        _save_agent_project(project)
        return {"project": project}
    if tool == "delete_character":
        project = _load_agent_project(str(args.get("project_id") or ""))
        characters = project.setdefault("characters", [])
        target = str(args.get("name") or "").strip()
        target_id = str(args.get("id") or "").strip()
        before = len(characters)
        project["characters"] = [
            item
            for item in characters
            if not (
                (target_id and item.get("id") == target_id)
                or (target and item.get("name") == target)
            )
        ]
        if len(project["characters"]) == before:
            raise KeyError(f"角色不存在: {target or target_id}")
        _save_agent_project(project)
        return {"project": project}
    if tool == "add_world_card":
        project = _load_agent_project(str(args.get("project_id") or ""))
        world = project.setdefault("world", [])
        world.append(
            {
                "id": f"world-{uuid.uuid4().hex[:10]}",
                "name": str(args.get("name") or "新设定"),
                "type": str(args.get("type") or "地点"),
                "summary": str(args.get("summary") or ""),
                "details": str(args.get("details") or ""),
                "significance": str(args.get("significance") or ""),
                "tags": str(args.get("tags") or ""),
            }
        )
        _save_agent_project(project)
        return {"project": project}
    if tool == "update_world_card":
        project = _load_agent_project(str(args.get("project_id") or ""))
        world = project.setdefault("world", [])
        target = str(args.get("name") or "").strip()
        target_id = str(args.get("id") or "").strip()
        card = next(
            (
                item
                for item in world
                if (target_id and item.get("id") == target_id)
                or (target and item.get("name") == target)
            ),
            None,
        )
        if card is None:
            raise KeyError(f"设定不存在: {target or target_id}")
        for key in ("name", "type", "summary", "details", "significance", "tags"):
            if key in args and args[key] is not None:
                card[key] = str(args[key])
        _save_agent_project(project)
        return {"project": project}
    if tool == "delete_world_card":
        project = _load_agent_project(str(args.get("project_id") or ""))
        world = project.setdefault("world", [])
        target = str(args.get("name") or "").strip()
        target_id = str(args.get("id") or "").strip()
        before = len(world)
        project["world"] = [
            item
            for item in world
            if not (
                (target_id and item.get("id") == target_id)
                or (target and item.get("name") == target)
            )
        ]
        if len(project["world"]) == before:
            raise KeyError(f"设定不存在: {target or target_id}")
        _save_agent_project(project)
        return {"project": project}
    if tool == "update_chapter":
        project = _load_agent_project(str(args.get("project_id") or ""))
        chapters = project.setdefault("chapters", [])
        target = str(args.get("chapter_id") or args.get("title") or "").strip()
        chapter = next(
            (
                item
                for item in chapters
                if item.get("id") == target or item.get("title") == target
            ),
            None,
        )
        if chapter is None:
            raise KeyError(f"章节不存在: {target}")
        if args.get("title") is not None:
            chapter["title"] = str(args["title"])
        if args.get("content") is not None:
            chapter["content"] = str(args["content"])
        _save_agent_project(project)
        return {"project": project}
    if tool == "delete_chapter":
        project = _load_agent_project(str(args.get("project_id") or ""))
        chapters = project.setdefault("chapters", [])
        target = str(args.get("chapter_id") or args.get("title") or "").strip()
        before = len(chapters)
        project["chapters"] = [
            item
            for item in chapters
            if not (item.get("id") == target or item.get("title") == target)
        ]
        if len(project["chapters"]) == before:
            raise KeyError(f"章节不存在: {target}")
        _save_agent_project(project)
        return {"project": project}
    if tool == "update_project":
        project = _load_agent_project(str(args.get("project_id") or ""))
        for key in ("name", "genre", "summary", "global_guidance"):
            if key in args and args[key] is not None:
                project[key] = str(args[key])
        if args.get("chapter_turns") is not None:
            try:
                project["chapter_turns"] = int(args["chapter_turns"])
            except (TypeError, ValueError):
                pass
        _save_agent_project(project)
        return {"project": project}
    if tool == "list_projects":
        return {"projects": _list_agent_projects()}
    if tool == "export_project":
        return {"project": _load_agent_project(str(args.get("project_id") or ""))}
    if tool == "export_book":
        book_id = str(args.get("book_id") or "")
        book = BOOK_STORE.get_book(book_id)
        chapters = [BOOK_STORE.get_chapter(book_id, row["id"]) for row in book["chapters"]]
        return {"book": book, "chapters": chapters}
    if tool == "merge_chapters":
        book = BOOK_STORE.merge_chapters(
            str(args.get("book_id") or ""),
            int(args.get("start_order") or 1),
            int(args.get("end_order") or 1),
            str(args.get("title") or ""),
        )
        return {"book": book}
    if tool == "evolution_start":
        state = start_run(
            project_id=str(args.get("project_id") or ""),
            project_name=str(args.get("project_name") or ""),
            genre=str(args.get("genre") or ""),
            characters=args.get("characters") or [],
            world=args.get("world") or [],
            map_nodes=args.get("map_nodes") or [],
            map_edges=args.get("map_edges") or [],
            settings=evolution_settings_from_dict(args.get("settings") or {}),
            seed=int(args["seed"]) if args.get("seed") not in (None, "") else None,
        )
        EVOLUTION_STORE.save(state)
        return {"evolution": _evolution_summary(state)}
    if tool == "evolution_advance":
        state = EVOLUTION_STORE.load(str(args.get("project_id") or ""))
        if state is None:
            raise KeyError("演化尚未开始")
        choice = str(args.get("choice_id") or "").strip() or None
        state, result = advance(state, choice_id=choice)
        EVOLUTION_STORE.save(state)
        summary = _evolution_summary(state)
        summary["message"] = turn_result_to_dict(result).get("message") or ""
        return {"evolution": summary}
    if tool == "evolution_guidance":
        state = EVOLUTION_STORE.load(str(args.get("project_id") or ""))
        if state is None:
            raise KeyError("演化尚未开始")
        state.guidance = str(args.get("guidance") or "").strip()
        EVOLUTION_STORE.save(state)
        return {"evolution": _evolution_summary(state)}
    if tool == "evolution_reset":
        project_id = str(args.get("project_id") or "").strip()
        EVOLUTION_STORE.delete(project_id)
        return {"ok": True, "deleted_project_id": project_id}
    if tool == "get_llm_config":
        return {"config": _llm_config_payload(_load_llm_config())}
    if tool == "get_server_status":
        return {
            "status": "ok",
            "embedded": _is_embedded(),
            "data_dir": str(DATA_ROOT),
            "projects": len(_list_agent_projects()),
            "books": len(BOOK_STORE.list_books()),
            "vault_connected": True if _is_embedded() else bool(VAULT_MANAGER.status().get("base_url")),
        }
    if tool == "update_llm_config":
        config = _load_llm_config()
        for key in ("base_url", "model", "preset"):
            if key in args and args[key] is not None:
                config[key] = str(args[key])
        _save_llm_config(config)
        return {"config": _llm_config_payload(config)}
    if tool == "save_knowledge":
        proposal = _embedded_vault().create_proposal(
            "story-workspace",
            str(args.get("title") or "AI 创作资料"),
            "Note",
            str(args.get("content") or ""),
            "experimental",
            [str(item) for item in (args.get("tags") or []) if str(item).strip()],
        )
        return {"proposal": proposal}
    if tool == "append_book_chapter":
        book = BOOK_STORE.append_chapter(
            str(args.get("book_id") or ""),
            str(args.get("title") or ""),
            str(args.get("content") or ""),
        )
        return {"book": book}
    if tool == "list_books":
        return {"books": BOOK_STORE.list_books()}
    if tool == "load_project":
        return {"project": _load_agent_project(str(args.get("project_id") or ""))}
    raise ValueError(f"未知工具: {tool}")


_AGENT_MUTATING_TOOLS = {
    "import_txt",
    "create_project",
    "append_chapter",
    "add_character",
    "update_character",
    "delete_character",
    "add_world_card",
    "update_world_card",
    "delete_world_card",
    "update_chapter",
    "delete_chapter",
    "update_project",
    "merge_chapters",
    "evolution_start",
    "evolution_advance",
    "evolution_guidance",
    "evolution_reset",
    "update_llm_config",
    "save_knowledge",
    "append_book_chapter",
}

_PROJECT_AGENT_TOOLS = {
    "append_chapter",
    "add_character",
    "update_character",
    "delete_character",
    "add_world_card",
    "update_world_card",
    "delete_world_card",
    "update_chapter",
    "delete_chapter",
    "update_project",
}

_BOOK_AGENT_TOOLS = {
    "append_book_chapter",
    "merge_chapters",
}


def _project_char_count(project: dict[str, Any]) -> int:
    return sum(len(str(chapter.get("content") or "")) for chapter in project.get("chapters") or [])


def _book_snapshot_payload(book_id: str) -> dict[str, Any]:
    book = BOOK_STORE.get_book(book_id)
    chapters = [
        {
            "id": row["id"],
            "title": row.get("title") or "",
            "order": row.get("order") or 0,
            "content": BOOK_STORE.get_chapter(book_id, row["id"])["content"],
        }
        for row in book["chapters"]
    ]
    return {"book_id": book_id, "chapters": chapters}


def _book_payload_char_count(payload: dict[str, Any]) -> int:
    return sum(len(str(chapter.get("content") or "")) for chapter in payload.get("chapters") or [])


def _auto_snapshot_for_tool(tool: str, args: dict[str, Any]) -> dict[str, Any] | None:
    try:
        if tool in _PROJECT_AGENT_TOOLS and str(args.get("project_id") or "").strip():
            project_id = str(args["project_id"]).strip()
            project = _load_agent_project(project_id)
            return VERSION_STORE.commit(
                "project",
                project_id,
                "AI 操作前快照",
                project,
                _project_char_count(project),
            )
        if tool in _BOOK_AGENT_TOOLS and str(args.get("book_id") or "").strip():
            book_id = str(args["book_id"]).strip()
            payload = _book_snapshot_payload(book_id)
            return VERSION_STORE.commit(
                "book",
                book_id,
                "AI 操作前快照",
                payload,
                _book_payload_char_count(payload),
            )
    except KeyError:
        return None
    return None


def _agent_system_prompt(attachments: list[dict[str, Any]]) -> str:
    tools = (
        "可用工具（需要操作时，单独一行输出 JSON：{\"tool\":\"工具名\",\"args\":{...}}）：\n"
        "- import_txt：参数 name, genre, text —— 把文本导入为 TXT 书（书架）\n"
        "- create_project：参数 name, genre, summary —— 新建故事项目\n"
        "- append_chapter：参数 project_id, title, content —— 给故事项目追加章节\n"
        "- add_character：参数 project_id, name, role, drive, fear, stance, identity, traits, background, secret\n"
        "- update_character：参数 project_id, name 或 id，以及要修改的字段（role, drive, fear, stance, identity, traits, background, secret 等）\n"
        "- delete_character：参数 project_id, name 或 id —— 删除角色（破坏性）\n"
        "- add_world_card：参数 project_id, name, type, summary, details, tags\n"
        "- update_world_card：参数 project_id, name 或 id 以及要修改的字段\n"
        "- delete_world_card：参数 project_id, name 或 id（破坏性）\n"
        "- update_chapter：参数 project_id, chapter_id 或 title，可修改 title/content\n"
        "- delete_chapter：参数 project_id, chapter_id 或 title（破坏性）\n"
        "- update_project：参数 project_id, name/genre/summary/global_guidance/chapter_turns\n"
        "- list_projects：无参数 —— 列出项目\n"
        "- export_project：参数 project_id —— 导出项目 JSON（只读）\n"
        "- export_book：参数 book_id —— 导出书与全部章节（只读）\n"
        "- merge_chapters：参数 book_id, start_order, end_order, title —— 合并书的连续章节\n"
        "- evolution_start：参数 project_id, project_name, genre, characters, world, seed —— 新建演化\n"
        "- evolution_advance：参数 project_id, choice_id —— 推进演化（choice_id 可选）\n"
        "- evolution_guidance：参数 project_id, guidance —— 设置演化引导\n"
        "- evolution_reset：参数 project_id —— 删除演化存档（破坏性）\n"
        "- get_llm_config：无参数 —— 查看 AI 配置（只读，不含密钥）\n"
        "- update_llm_config：参数 base_url/model/preset —— 修改 AI 配置（不写 API Key）\n"
        "- get_server_status：无参数 —— 查看服务与数据状态（只读）\n"
        "- save_knowledge：参数 title, content, tags —— 保存为资料草稿\n"
        "- append_book_chapter：参数 book_id, title, content —— 给 TXT 书追加章节\n"
        "- list_books：无参数 —— 列出书架\n"
        "- load_project：参数 project_id —— 读取故事项目\n"
    )
    attach_block = ""
    if attachments:
        lines: list[str] = []
        for attachment in attachments[:5]:
            kind = str(attachment.get("kind") or "txt")
            name = str(attachment.get("name") or "附件")
            text = str(attachment.get("text") or "")
            if kind == "project":
                try:
                    project = json.loads(text)
                    preview = json.dumps(
                        {key: project.get(key) for key in ("id", "name", "genre", "summary")},
                        ensure_ascii=False,
                    )
                except (ValueError, TypeError):
                    preview = text[:300]
            else:
                preview = text[:600]
            lines.append(f"- {name}（{kind}）：{preview}")
        attach_block = "\n\n用户附件：\n" + "\n".join(lines)
    return (
        "你是 Rhine-Lore 的创作助手，可以读写本地工作区（故事项目、TXT 书架、知识库）。"
        "规则：普通创作对话直接回复正文或建议，不要调用工具；"
        "当用户要求导入、新建项目、追加章节、添加角色/设定、保存资料、操作书架时，"
        "先调用对应工具并给出完整参数（例如角色卡的姓名、身份、欲望、恐惧、立场、特质、"
        "背景、秘密），但创建/修改类操作会先作为“提案”返回给用户确认，不会立即执行；"
        "用户确认后会单独执行。只读操作（list_books / load_project）可以直接执行。\n\n"
        + tools
        + attach_block
    )


def _extract_agent_tool_call(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{\s*\"tool\"\s*:", text)
    if not match:
        return None
    start = match.start()
    depth = 0
    end = -1
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    if end < 0:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    tool = str(data.get("tool") or "").strip()
    if not tool:
        return None
    args = data.get("args")
    return {"tool": tool, "args": args if isinstance(args, dict) else {}}


def _resolve_llm(payload_llm: dict[str, Any] | None = None) -> dict[str, str]:
    stored = _load_llm_config()
    explicit = payload_llm or {}
    return {
        "base_url": str(explicit.get("base_url") or stored.get("base_url") or "").strip(),
        "api_key": str(explicit.get("api_key") or stored.get("api_key") or "").strip(),
        "model": str(explicit.get("model") or stored.get("model") or "").strip(),
    }


def _chat_with_vault(messages: list[dict[str, str]], llm: dict[str, Any]) -> str:
    """Call the local Vault OpenAI-compatible chat endpoint and return text."""
    if os.environ.get("RHINE_LORE_EMBEDDED") == "1":
        base = str(llm.get("base_url") or "").rstrip("/")
        if not base or not llm.get("model"):
            raise ValueError("未配置 API 地址或模型")
        payload = {"model": llm["model"], "messages": messages, "stream": False}
        request = Request(
            base + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {llm['api_key']}",
            },
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"AI 返回格式异常：{data}") from exc
    vault_base = VAULT_MANAGER.status()["base_url"]
    target = _join_base_and_path(vault_base, "/api/llm/openai-compatible/chat")
    chat_body = {
        "workspace_id": "story-workspace",
        "base_url": str(llm.get("base_url") or "").strip() or None,
        "api_key": str(llm.get("api_key") or "").strip(),
        "model": str(llm.get("model") or "").strip() or None,
        "messages": messages,
    }
    request = Request(
        target,
        data=json.dumps(chat_body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    text = str(result.get("answer") or "").strip()
    if not text:
        raise ValueError("AI 返回为空")
    return text


def _run_agent_chat(
    raw_messages: list[dict[str, Any]],
    attachments: list[Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the agent loop: call the model, execute read-only tools, return final text + actions."""
    llm = _resolve_llm(None)
    if not llm["api_key"]:
        raise ValueError("未配置 API Key")
    messages = [
        {"role": str(item.get("role") or "user"), "content": str(item.get("content") or "")}
        for item in raw_messages
    ]
    working: list[dict[str, str]] = [
        {"role": "system", "content": _agent_system_prompt(attachments or [])},
        *messages,
    ]
    actions: list[dict[str, Any]] = []
    final_text = ""
    for step in range(5):
        text = _chat_with_vault(working, llm)
        call = _extract_agent_tool_call(text)
        if call is None:
            final_text = text
            break
        if call["tool"] in _AGENT_MUTATING_TOOLS:
            actions.append(
                {
                    "tool": call["tool"],
                    "args": call["args"],
                    "pending": True,
                    "result": None,
                }
            )
            final_text = text
            break
        result_payload: dict[str, Any] | None = None
        try:
            result = _run_agent_tool(call["tool"], call["args"])
            result_payload = result
            result_text = json.dumps(result, ensure_ascii=False)[:1200]
            summary = f"工具 {call['tool']} 执行成功：{result_text}"
        except Exception as exc:  # noqa: BLE001 - tool errors go back to the model
            result_payload = {"error": str(exc)}
            summary = f"工具 {call['tool']} 执行失败：{exc}"
        actions.append(
            {
                "tool": call["tool"],
                "args": call["args"],
                "result": result_payload,
            }
        )
        working.append({"role": "assistant", "content": text})
        working.append({"role": "user", "content": summary})
        if step >= 3:
            working.append(
                {
                    "role": "user",
                    "content": "请基于以上工具结果直接输出最终中文回复，不要再调用工具。",
                }
            )
    if not final_text:
        final_text = _chat_with_vault(working, llm)
    return final_text, actions


def _store_turn_prose(
    state: EvolutionState,
    viewpoint_id: str,
    llm: dict[str, Any],
    global_guidance: str = "",
    variation: str = "",
    turn_override: int | None = None,
    writing_style: str = "",
    style_card: str = "",
    quality_pass: bool = False,
) -> bool:
    """Generate prose for the latest (or specified) turn and store it in state."""
    api_key = str(llm.get("api_key") or "").strip()
    if not api_key:
        return False
    messages = build_ai_prose_prompt(
        state,
        viewpoint_id,
        global_guidance=global_guidance,
        variation=variation,
        writing_style=writing_style,
        style_card=style_card,
    )
    text = _chat_with_vault(messages, llm)
    if quality_pass:
        text = _polish_text(text, llm, style_card)
    latest_turn = (
        turn_override
        if turn_override is not None
        else (state.history[-1].turn if state.history else state.turn)
    )
    prose_key = f"{latest_turn}:{viewpoint_id or (state.cast[0].id if state.cast else '')}"
    state.ai_prose[prose_key] = text
    _prune_ai_prose(state)
    return True


def _prune_ai_prose(state: EvolutionState) -> None:
    min_turn = max(1, state.turn - 20)
    kept: dict[str, str] = {}
    for key, value in state.ai_prose.items():
        parts = key.split(":")
        if not parts or not parts[0]:
            continue
        if parts[0].isdigit():
            if int(parts[0]) >= min_turn:
                kept[key] = value
        elif parts[0] == "chapter" and len(parts) >= 2 and parts[1].isdigit():
            if int(parts[1]) >= min_turn:
                kept[key] = value
    state.ai_prose = kept


def _store_chapter_prose(
    state: EvolutionState,
    start_turn: int,
    end_turn: int,
    viewpoint_id: str,
    llm: dict[str, Any],
    global_guidance: str = "",
    variation: str = "",
    writing_style: str = "",
    style_card: str = "",
    quality_pass: bool = False,
) -> bool:
    api_key = str(llm.get("api_key") or "").strip()
    if not api_key:
        return False
    snapshot = _chapter_snapshot(state, end_turn)
    messages = build_ai_prose_prompt(
        snapshot,
        viewpoint_id,
        global_guidance=global_guidance,
        variation=variation,
        writing_style=writing_style,
        style_card=style_card,
    )
    text = _chat_with_vault(messages, llm)
    if quality_pass:
        text = _polish_text(text, llm, style_card)
    key = f"chapter:{start_turn}:{viewpoint_id or (state.cast[0].id if state.cast else '')}"
    state.ai_prose[key] = text
    _prune_ai_prose(state)
    return True


def _polish_text(text: str, llm: dict[str, Any], style_card: str = "") -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "你是中文小说润色编辑。保持事件、设定、人物与时间线完全不变，"
                "只提升文学质感、节奏与细节，删除 AI 腔套话。"
                + (f"风格基准（润色后必须保持）：{style_card}" if style_card else "")
                + QUALITY_GUIDE
            ),
        },
        {"role": "user", "content": f"请润色以下正文，直接输出润色后的完整正文，不要解释：\n\n{text}"},
    ]
    return _chat_with_vault(messages, llm)


def _chapter_snapshot(state: EvolutionState, end_turn: int) -> EvolutionState:
    """Snapshot of the story up to a chapter's last turn for regeneration."""
    snapshot = copy.deepcopy(state)
    snapshot.history = [event for event in snapshot.history if event.turn <= end_turn]
    snapshot.ai_prose = {
        key: value
        for key, value in snapshot.ai_prose.items()
        if int(key.split(":")[0]) <= end_turn
    }
    snapshot.turn = end_turn
    return snapshot


def _lan_addresses() -> list[str]:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("10.255.255.255", 1))
        address = probe.getsockname()[0]
        probe.close()
        return [address] if address else []
    except OSError:
        return []


class RhineLoreHandler(SimpleHTTPRequestHandler):
    server_version = "RhineLore/0.1"

    def __init__(self, *args: Any, directory: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, directory=directory, **kwargs)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.startswith("/lore-api/"):
            self._handle_lore_api()
            return
        if self.path.startswith("/vault-proxy") or self.path.startswith("/api/"):
            if _is_embedded() and self.path.startswith("/api/"):
                self._handle_embedded_api()
                return
            self._proxy_to_vault()
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith("/lore-api/"):
            self._handle_lore_api()
            return
        if self.path.startswith("/vault-proxy") or self.path.startswith("/api/"):
            if _is_embedded() and self.path.startswith("/api/"):
                self._handle_embedded_api()
                return
            self._proxy_to_vault()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_PATCH(self) -> None:
        if self.path.startswith("/vault-proxy") or self.path.startswith("/api/"):
            if _is_embedded() and self.path.startswith("/api/"):
                self._handle_embedded_api()
                return
            self._proxy_to_vault()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_DELETE(self) -> None:
        if self.path.startswith("/lore-api/books/"):
            book_id = self.path[len("/lore-api/books/") :].strip("/")
            if not book_id:
                self._send_json(400, {"error": "book_id 为空"})
                return
            try:
                BOOK_STORE.delete_book(book_id)
                self._send_json(200, {"ok": True, "book_id": book_id})
            except KeyError as exc:
                self._send_json(404, {"error": str(exc)})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        super().end_headers()

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length else b""

    def _read_json_body(self) -> dict[str, Any]:
        body = self._read_body()
        if not body:
            return {}
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _send_json(self, status: int, payload: Any) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _stream_llm_answer(
        self,
        text: str,
        actions: list[dict[str, Any]],
        model: str,
    ) -> None:
        """SSE 打字机流式输出：正文分片下发，结束后发送 done 事件。"""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.end_headers()

        def emit(event_type: str, payload: dict[str, Any]) -> None:
            data = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(data)
            self.wfile.flush()

        emit("start", {"type": "start", "model": model, "provider": "openai-compatible"})
        chunk_size = 6
        for index in range(0, len(text), chunk_size):
            emit("delta", {"type": "delta", "text": text[index : index + chunk_size]})
            time.sleep(0.012)
        emit("done", {"type": "done", "answer": text, "actions": actions})

    def _vault_status_payload(self) -> dict[str, Any]:
        if _is_embedded():
            port = self.server.server_address[1] if self.server else 8786
            return {
                "config": _default_vault_config(),
                "manager": {
                    "managed": False,
                    "running": True,
                    "pid": os.getpid(),
                    "returncode": None,
                    "base_url": f"http://127.0.0.1:{port}/",
                    "vault_path": str(DEFAULT_VAULT_CHECKOUT),
                    "command": [],
                    "mode": "embedded",
                    "auto_start": {"enabled": False, "attempted": False, "error": ""},
                },
                "connected": True,
                "health": {"connected": True, "status": "ok", "mode": "embedded"},
            }
        manager_status = VAULT_MANAGER.status()
        base_url = manager_status["base_url"] or DEFAULT_VAULT_URL
        return {
            "config": _default_vault_config(),
            "manager": manager_status,
            **_vault_health(base_url),
        }

    def _handle_embedded_api(self) -> None:
        parsed_request = urlparse(self.path)
        path = parsed_request.path
        query = parse_qs(parsed_request.query)
        vault = _embedded_vault()
        try:
            if self.command == "GET" and path == "/api/health":
                self._send_json(200, vault.health())
                return
            if self.command == "GET" and path == "/api/workspaces":
                self._send_json(200, vault.workspaces())
                return
            if self.command == "POST" and path == "/api/workspaces":
                body = self._read_json_body()
                workspace = vault.create_workspace(
                    str(body.get("workspace_id") or ""),
                    str(body.get("workspace_type") or "project"),
                    str(body.get("display_name") or ""),
                )
                self._send_json(200, workspace)
                return
            if self.command == "GET" and path == "/api/nodes":
                workspace_id = (query.get("workspace_id") or [""])[0].strip()
                self._send_json(200, vault.nodes(workspace_id))
                return
            if self.command == "POST" and path == "/api/manual":
                body = self._read_json_body()
                proposal = vault.create_proposal(
                    str(body.get("workspace_id") or ""),
                    str(body.get("title") or ""),
                    str(body.get("node_type") or "Note"),
                    str(body.get("content") or ""),
                    str(body.get("authority") or "experimental"),
                    list(body.get("tags") or []),
                )
                self._send_json(200, proposal)
                return
            if self.command == "GET" and path == "/api/proposals":
                workspace_id = (query.get("workspace_id") or [""])[0].strip()
                self._send_json(200, vault.proposals(workspace_id))
                return
            if (
                self.command == "POST"
                and path.startswith("/api/proposals/")
                and path.endswith("/stage")
            ):
                proposal_id = path[len("/api/proposals/") : -len("/stage")]
                body = self._read_json_body()
                workspace_id = str(body.get("workspace_id") or "")
                temporary_ids = [str(item) for item in (body.get("temporary_ids") or [])]
                result = vault.stage_proposal(workspace_id, proposal_id, temporary_ids)
                self._send_json(200, result)
                return
            if self.command == "GET" and path == "/api/staging":
                workspace_id = (query.get("workspace_id") or [""])[0].strip()
                status = (query.get("status") or [""])[0].strip() or None
                self._send_json(200, vault.staging(workspace_id, status))
                return
            if self.command == "POST" and path == "/api/staging/approve":
                body = self._read_json_body()
                workspace_id = str(body.get("workspace_id") or "")
                entry_ids = [str(item) for item in (body.get("entry_ids") or [])]
                result = vault.approve_staging(workspace_id, entry_ids)
                self._send_json(200, result)
                return
            if self.command == "POST" and path == "/api/context":
                body = self._read_json_body()
                workspace_id = str(body.get("workspace_id") or "")
                query_text = str(body.get("query") or "")
                limit = int(body.get("result_limit") or 10)
                tags = list(body.get("tags") or [])
                results = vault.search(workspace_id, query_text, tags, limit)
                context = "\n\n".join(
                    f"### {item['title']}\n{item['content']}" for item in results
                )
                self._send_json(
                    200,
                    {
                        "query": query_text,
                        "results": results,
                        "context": context,
                        "note": "内嵌资料库检索结果",
                    },
                )
                return
            if self.command == "POST" and path == "/api/documents/generate":
                body = self._read_json_body()
                workspace_id = str(body.get("workspace_id") or "")
                query_text = str(body.get("query") or "")
                limit = int(body.get("result_limit") or 10)
                tags = list(body.get("tags") or [])
                title = str(body.get("title") or "Story Bible")
                results = vault.search(workspace_id, query_text, tags, limit)
                lines = [f"# {title}", ""]
                if results:
                    for item in results:
                        lines.append(f"## {item['title']}")
                        lines.append(f"类型：{item['node_type']}")
                        lines.append("")
                        lines.append(item["content"])
                        lines.append("")
                else:
                    lines.append("（暂无已入库资料，先在「资料草稿」中保存并确认入库。）")
                self._send_json(
                    200,
                    {"title": title, "markdown": "\n".join(lines), "count": len(results)},
                )
                return
            if self.command == "POST" and path == "/api/llm/fake":
                body = self._read_json_body()
                query_text = str(body.get("query") or "")
                self._send_json(
                    200,
                    {
                        "answer": f"（离线模板）关于「{query_text}」的检索结果已就绪，可查看上下文面板。",
                        "query": query_text,
                    },
                )
                return
            if self.command == "POST" and path == "/api/llm/openai-compatible/chat":
                body = self._read_json_body()
                messages = body.get("messages") or []
                llm = _resolve_llm(body.get("llm"))
                text = _chat_with_vault(messages, llm)
                self._send_json(200, {"answer": text})
                return
            if self.command == "POST" and path == "/api/llm/openai-compatible/ping":
                body = self._read_json_body()
                messages = [{"role": "user", "content": str(body.get("message") or "你好")}]
                llm = _resolve_llm(body.get("llm"))
                text = _chat_with_vault(messages, llm)
                self._send_json(200, {"ok": True, "answer": text})
                return
            self._send_json(404, {"error": f"未知的内嵌资料库接口: {self.command} {path}"})
        except KeyError as exc:
            self._send_json(404, {"error": str(exc)})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - surface failures to the UI
            self._send_json(500, {"error": str(exc)})

    def _handle_lore_api(self) -> None:
        parsed_request = urlparse(self.path)
        try:
            if self.command == "GET" and parsed_request.path == "/lore-api/vault/status":
                self._send_json(200, self._vault_status_payload())
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/vault/web/status":
                if _is_embedded():
                    port = self.server.server_address[1] if self.server else 8786
                    self._send_json(
                        200,
                        {
                            "vault_path": str(DEFAULT_VAULT_CHECKOUT),
                            "installed": True,
                            "installable": False,
                            "url": f"http://127.0.0.1:{port}/",
                            "web_root": "",
                            "package_dir": "",
                            "install_command": [],
                            "error": "",
                        },
                    )
                    return
                self._send_json(200, _vault_web_status(base_url=VAULT_MANAGER.status()["base_url"]))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/vault/web/install":
                if _is_embedded():
                    self._send_json(200, self._vault_status_payload())
                    return
                payload = self._read_json_body()
                raw_path = str(payload.get("vault_path") or "").strip()
                vault_path = Path(raw_path) if raw_path else None
                self._send_json(200, _install_vault_web(vault_path))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/vault/connect":
                if _is_embedded():
                    self._send_json(200, self._vault_status_payload())
                    return
                payload = self._read_json_body()
                if "base_url" in payload and str(payload["base_url"]).strip():
                    base_url = str(payload["base_url"]).strip().rstrip("/")
                else:
                    host = _coerce_local_host(payload.get("host"))
                    port = _coerce_port(payload.get("port", DEFAULT_VAULT_PORT))
                    base_url = f"http://{host}:{port}"
                VAULT_MANAGER.connect(base_url)
                self._send_json(200, self._vault_status_payload())
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/vault/start":
                if _is_embedded():
                    self._send_json(200, self._vault_status_payload())
                    return
                payload = self._read_json_body()
                host = _coerce_local_host(payload.get("host"))
                port = _coerce_port(payload.get("port", DEFAULT_VAULT_PORT))
                vault_path = Path(str(payload.get("vault_path") or DEFAULT_VAULT_CHECKOUT))
                database_path = Path(str(payload["database_path"])) if str(payload.get("database_path") or "").strip() else DEFAULT_VAULT_DATABASE
                python_path = Path(str(payload["python_path"])) if str(payload.get("python_path") or "").strip() else None
                VAULT_MANAGER.start(
                    vault_path=vault_path,
                    host=host,
                    port=port,
                    database_path=database_path,
                    python_path=python_path,
                )
                self._send_json(200, self._vault_status_payload())
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/vault/stop":
                if _is_embedded():
                    self._send_json(200, self._vault_status_payload())
                    return
                VAULT_MANAGER.stop()
                self._send_json(200, self._vault_status_payload())
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/evolution/state":
                query = parse_qs(parsed_request.query)
                project_id = (query.get("project_id") or [""])[0].strip()
                viewpoint_id = (query.get("viewpoint_id") or [""])[0].strip()
                state = EVOLUTION_STORE.load(project_id)
                if state is None:
                    self._send_json(404, {"error": "演化尚未开始"})
                    return
                self._send_json(200, _evolution_payload(state, viewpoint_id=viewpoint_id))
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/lan":
                port = self.server.server_address[1] if self.server else 8786
                addresses = _lan_addresses()
                self._send_json(
                    200,
                    {
                        "addresses": addresses,
                        "port": port,
                        "local_url": f"http://127.0.0.1:{port}/",
                        "lan_urls": [f"http://{address}:{port}/" for address in addresses],
                    },
                )
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/books":
                self._send_json(200, {"books": BOOK_STORE.list_books()})
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/books/import":
                payload = self._read_json_body()
                text = str(payload.get("text") or "")
                if not text.strip():
                    raise ValueError("TXT 内容为空，无法导入")
                book = BOOK_STORE.import_txt(
                    name=str(payload.get("name") or "未命名小说"),
                    text=text,
                    genre=str(payload.get("genre") or ""),
                    summary=str(payload.get("summary") or ""),
                )
                self._send_json(200, book)
                return
            if "/lore-api/books/" in parsed_request.path and "/chapters/" in parsed_request.path:
                parts = parsed_request.path[len("/lore-api/books/") :].split("/")
                if len(parts) == 3 and parts[1] == "chapters":
                    book_id, _, chapter_id = parts
                    if self.command == "GET":
                        self._send_json(200, {"chapter": BOOK_STORE.get_chapter(book_id, chapter_id)})
                        return
                    if self.command == "POST":
                        payload = self._read_json_body()
                        chapter = BOOK_STORE.save_chapter(
                            book_id,
                            chapter_id,
                            str(payload.get("title") or ""),
                            str(payload.get("content") or ""),
                        )
                        self._send_json(200, {"chapter": chapter})
                        return
            if self.command == "POST" and parsed_request.path.endswith("/ai/write") and "/lore-api/books/" in parsed_request.path:
                book_id = parsed_request.path[len("/lore-api/books/") : -len("/ai/write")].strip("/")
                payload = self._read_json_body()
                chapter_id = str(payload.get("chapter_id") or "").strip()
                mode = str(payload.get("mode") or "continue").strip()
                if mode not in {"continue", "rewrite", "expand"}:
                    mode = "continue"
                messages = BOOK_STORE.build_ai_write_messages(
                    book_id,
                    chapter_id,
                    mode,
                    str(payload.get("guidance") or ""),
                    text=str(payload.get("text") or "") or None,
                )
                llm = _resolve_llm(payload.get("llm"))
                if not llm.get("api_key") or not llm.get("base_url") or not llm.get("model"):
                    self._send_json(200, {"text": _offline_ai_write(mode), "offline": True})
                    return
                try:
                    text = _chat_with_vault(messages, llm)
                except Exception as exc:  # noqa: BLE001 - surface AI errors
                    self._send_json(502, {"error": f"AI 调用失败：{exc}"})
                    return
                self._send_json(200, {"text": text, "offline": False})
                return
            if self.command == "POST" and parsed_request.path.endswith("/analyze") and "/lore-api/books/" in parsed_request.path:
                book_id = parsed_request.path[len("/lore-api/books/") : -len("/analyze")].strip("/")
                payload = self._read_json_body()
                llm = _resolve_llm(payload.get("llm"))
                if llm.get("api_key") and llm.get("base_url") and llm.get("model"):
                    messages = BOOK_STORE.build_analyze_messages(book_id)
                    try:
                        text = _chat_with_vault(messages, llm)
                        analysis = BOOK_STORE.store_analysis(book_id, text)
                        self._send_json(200, {"analysis": analysis, "offline": False})
                    except Exception as exc:  # noqa: BLE001 - surface AI errors
                        self._send_json(502, {"error": f"AI 分析失败：{exc}"})
                else:
                    analysis = BOOK_STORE.book_analysis(book_id)
                    self._send_json(200, {"analysis": analysis, "offline": True})
                return
            if (
                self.command == "POST"
                and parsed_request.path.endswith("/summary")
                and "/lore-api/books/" in parsed_request.path
                and "/chapters/" in parsed_request.path
            ):
                parts = parsed_request.path[len("/lore-api/books/") : -len("/summary")].split("/")
                if len(parts) == 3 and parts[1] == "chapters":
                    book_id, _, chapter_id = parts
                    payload = self._read_json_body()
                    llm = _resolve_llm(payload.get("llm"))
                    if llm.get("api_key") and llm.get("base_url") and llm.get("model"):
                        messages = BOOK_STORE.build_summary_messages(book_id, chapter_id)
                        try:
                            text = _chat_with_vault(messages, llm)
                            summary = BOOK_STORE.store_chapter_summary(book_id, chapter_id, text)
                            self._send_json(200, {"summary": summary, "offline": False})
                        except Exception as exc:  # noqa: BLE001 - surface AI errors
                            self._send_json(502, {"error": f"AI 摘要失败：{exc}"})
                    else:
                        chapter = BOOK_STORE.get_chapter(book_id, chapter_id)
                        self._send_json(
                            200,
                            {"summary": _heuristic_summary(chapter["content"]), "offline": True},
                        )
                    return
            if self.command == "GET" and parsed_request.path.startswith("/lore-api/books/"):
                book_id = parsed_request.path[len("/lore-api/books/") :].strip("/")
                if book_id:
                    self._send_json(200, {"book": BOOK_STORE.get_book(book_id)})
                    return
            if self.command == "GET" and parsed_request.path == "/lore-api/llm/config":
                self._send_json(200, _llm_config_payload(_load_llm_config()))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/llm/config":
                payload = self._read_json_body()
                config = _load_llm_config()
                if str(payload.get("base_url") or "").strip():
                    config["base_url"] = str(payload["base_url"]).strip()
                if str(payload.get("api_key") or "").strip():
                    config["api_key"] = str(payload["api_key"]).strip()
                elif payload.get("clear_key") is True:
                    config["api_key"] = ""
                if str(payload.get("model") or "").strip():
                    config["model"] = str(payload["model"]).strip()
                if str(payload.get("preset") or "").strip():
                    config["preset"] = str(payload["preset"]).strip()
                _save_llm_config(config)
                self._send_json(200, _llm_config_payload(config))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/llm/ping":
                payload = self._read_json_body()
                llm = _resolve_llm(None)
                if not llm["api_key"]:
                    self._send_json(400, {"error": "未配置 API Key"})
                    return
                messages = [
                    {
                        "role": "system",
                        "content": "Reply normally and briefly. This is a provider connectivity test.",
                    },
                    {"role": "user", "content": str(payload.get("message") or "你好")},
                ]
                try:
                    text = _chat_with_vault(messages, llm)
                except HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")[-300:]
                    self._send_json(502, {"error": f"AI 连接失败：{detail or exc}"})
                    return
                except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                    self._send_json(502, {"error": f"AI 连接失败：{exc}"})
                    return
                self._send_json(200, {"answer": text, "model": llm["model"], "provider": "openai-compatible"})
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/llm/chat":
                payload = self._read_json_body()
                raw_messages = payload.get("messages") or []
                if not isinstance(raw_messages, list) or not raw_messages:
                    raise ValueError("messages 不能为空")
                raw_attachments = payload.get("attachments")
                attachments = raw_attachments if isinstance(raw_attachments, list) else []
                if not _resolve_llm(None)["api_key"]:
                    self._send_json(400, {"error": "未配置 API Key"})
                    return
                try:
                    final_text, actions = _run_agent_chat(raw_messages, attachments)
                except HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")[-300:]
                    self._send_json(502, {"error": f"AI 请求失败：{detail or exc}"})
                    return
                except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                    self._send_json(502, {"error": f"AI 请求失败：{exc}"})
                    return
                self._send_json(
                    200,
                    {
                        "answer": final_text,
                        "model": _resolve_llm(None)["model"],
                        "provider": "openai-compatible",
                        "actions": actions,
                    },
                )
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/llm/chat/stream":
                payload = self._read_json_body()
                raw_messages = payload.get("messages") or []
                if not isinstance(raw_messages, list) or not raw_messages:
                    raise ValueError("messages 不能为空")
                raw_attachments = payload.get("attachments")
                attachments = raw_attachments if isinstance(raw_attachments, list) else []
                if not _resolve_llm(None)["api_key"]:
                    self._send_json(400, {"error": "未配置 API Key"})
                    return
                try:
                    final_text, actions = _run_agent_chat(raw_messages, attachments)
                except HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")[-300:]
                    self._send_json(502, {"error": f"AI 请求失败：{detail or exc}"})
                    return
                except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                    self._send_json(502, {"error": f"AI 请求失败：{exc}"})
                    return
                self._stream_llm_answer(final_text, actions, _resolve_llm(None)["model"])
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/agent/execute":
                payload = self._read_json_body()
                tool = str(payload.get("tool") or "").strip()
                args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
                if tool not in _AGENT_MUTATING_TOOLS:
                    self._send_json(400, {"error": "只允许执行已确认的写操作"})
                    return
                snapshot = _auto_snapshot_for_tool(tool, args)
                try:
                    result = _run_agent_tool(tool, args)
                except KeyError as exc:
                    self._send_json(404, {"error": str(exc)})
                    return
                except ValueError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                self._send_json(
                    200,
                    {"ok": True, "tool": tool, "result": result, "snapshot": snapshot},
                )
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/versions/commit":
                payload = self._read_json_body()
                kind = str(payload.get("kind") or "").strip()
                entity_id = str(payload.get("entity_id") or "").strip()
                if kind not in {"project", "book"} or not entity_id:
                    raise ValueError("kind 必须是 project/book，且 entity_id 不能为空")
                message = str(payload.get("message") or "未命名版本")
                raw = payload.get("payload")
                if raw is None:
                    if kind == "project":
                        project = _load_agent_project(entity_id)
                        raw = project
                        char_count = _project_char_count(project)
                    else:
                        raw = _book_snapshot_payload(entity_id)
                        char_count = _book_payload_char_count(raw)
                else:
                    char_count = (
                        _project_char_count(raw)
                        if kind == "project"
                        else _book_payload_char_count(raw)
                    )
                snapshot = VERSION_STORE.commit(kind, entity_id, message, raw, char_count)
                self._send_json(200, {"snapshot": snapshot})
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/versions":
                query = parse_qs(parsed_request.query)
                kind = (query.get("kind") or [""])[0].strip()
                entity_id = (query.get("entity_id") or [""])[0].strip()
                if kind not in {"project", "book"} or not entity_id:
                    raise ValueError("kind 必须是 project/book，且 entity_id 不能为空")
                self._send_json(200, {"versions": VERSION_STORE.history(kind, entity_id)})
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/versions/restore":
                payload = self._read_json_body()
                kind = str(payload.get("kind") or "").strip()
                entity_id = str(payload.get("entity_id") or "").strip()
                snapshot_id = str(payload.get("snapshot_id") or "").strip()
                if kind not in {"project", "book"} or not entity_id or not snapshot_id:
                    raise ValueError("参数不完整")
                pre_snapshot = None
                try:
                    if kind == "project":
                        project = _load_agent_project(entity_id)
                        pre_snapshot = VERSION_STORE.commit(
                            "project",
                            entity_id,
                            "恢复前快照",
                            project,
                            _project_char_count(project),
                        )
                    else:
                        current = _book_snapshot_payload(entity_id)
                        pre_snapshot = VERSION_STORE.commit(
                            "book",
                            entity_id,
                            "恢复前快照",
                            current,
                            _book_payload_char_count(current),
                        )
                except KeyError:
                    pre_snapshot = None
                loaded = VERSION_STORE.load_snapshot(kind, entity_id, snapshot_id)
                restored_payload = loaded["payload"]
                if kind == "project":
                    if (
                        not isinstance(restored_payload, dict)
                        or not str(restored_payload.get("id") or "").strip()
                    ):
                        raise ValueError("快照内容损坏")
                    _save_agent_project(restored_payload)
                    self._send_json(
                        200,
                        {"payload": restored_payload, "snapshot": pre_snapshot},
                    )
                    return
                if (
                    not isinstance(restored_payload, dict)
                    or not isinstance(restored_payload.get("chapters"), list)
                ):
                    raise ValueError("快照内容损坏")
                book = BOOK_STORE.restore_book(entity_id, restored_payload["chapters"])
                chapters = [
                    BOOK_STORE.get_chapter(entity_id, row["id"]) for row in book["chapters"]
                ]
                self._send_json(
                    200,
                    {
                        "payload": {"book": book, "chapters": chapters},
                        "snapshot": pre_snapshot,
                    },
                )
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/start":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                if not project_id:
                    raise ValueError("project_id 不能为空")
                seed_raw = payload.get("seed")
                seed = int(seed_raw) if seed_raw not in (None, "") else None
                map_data = payload.get("map") or {}
                state = start_run(
                    project_id=project_id,
                    project_name=str(payload.get("project_name") or ""),
                    genre=str(payload.get("genre") or ""),
                    characters=payload.get("characters") or [],
                    world=payload.get("world") or [],
                    map_nodes=map_data.get("nodes") or [],
                    map_edges=map_data.get("edges") or [],
                    settings=evolution_settings_from_dict(payload.get("settings")),
                    seed=seed,
                )
                EVOLUTION_STORE.save(state)
                self._send_json(200, _evolution_payload(state))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/advance":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                state = EVOLUTION_STORE.load(project_id)
                if state is None:
                    self._send_json(404, {"error": "演化尚未开始"})
                    return
                choice_raw = payload.get("choice_id")
                choice_id = str(choice_raw).strip() if choice_raw not in (None, "") else None
                viewpoint_id = str(payload.get("viewpoint_id") or "").strip()
                state, result = advance(state, choice_id=choice_id)
                EVOLUTION_STORE.save(state)
                self._send_json(200, _evolution_payload(state, result, viewpoint_id))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/ai-prose":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                state = EVOLUTION_STORE.load(project_id)
                if state is None:
                    self._send_json(404, {"error": "演化尚未开始"})
                    return
                viewpoint_id = str(payload.get("viewpoint_id") or "").strip()
                llm = _resolve_llm(payload.get("llm"))
                api_key = str(llm.get("api_key") or "").strip()
                if not api_key:
                    self._send_json(400, {"error": "未配置 API Key"})
                    return
                global_guidance = str(payload.get("global_guidance") or "").strip()
                variation = str(payload.get("variation") or "").strip()
                writing_style = str(payload.get("writing_style") or "").strip()
                style_card = str(payload.get("style_card") or "").strip()
                quality_pass = bool(payload.get("quality_pass") or False)
                try:
                    _store_turn_prose(
                        state,
                        viewpoint_id,
                        llm,
                        global_guidance,
                        variation,
                        writing_style=writing_style,
                        style_card=style_card,
                        quality_pass=quality_pass,
                    )
                except HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")[-300:]
                    self._send_json(502, {"error": f"AI 生成失败：{detail or exc}"})
                    return
                except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                    self._send_json(502, {"error": f"AI 生成失败：{exc}"})
                    return
                EVOLUTION_STORE.save(state)
                self._send_json(200, _evolution_payload(state, viewpoint_id=viewpoint_id))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/advance-chapter":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                state = EVOLUTION_STORE.load(project_id)
                if state is None:
                    self._send_json(404, {"error": "演化尚未开始"})
                    return
                viewpoint_id = str(payload.get("viewpoint_id") or "").strip()
                turns = max(1, min(8, int(payload.get("turns") or 4)))
                llm = _resolve_llm(payload.get("llm"))
                api_key = str(llm.get("api_key") or "").strip()
                global_guidance = str(payload.get("global_guidance") or "").strip()
                writing_style = str(payload.get("writing_style") or "").strip()
                style_card = str(payload.get("style_card") or "").strip()
                quality_pass = bool(payload.get("quality_pass") or False)
                advanced = 0
                iterations = 0
                result: TurnResult | None = None
                start_turn = state.turn + 1
                while advanced < turns and not state.ending and iterations < 40:
                    state, result = advance(state, choice_id="fate")
                    iterations += 1
                    if result.advanced:
                        advanced += 1
                if api_key:
                    try:
                        _store_chapter_prose(
                            state,
                            start_turn,
                            state.turn,
                            viewpoint_id,
                            llm,
                            global_guidance,
                            writing_style=writing_style,
                            style_card=style_card,
                            quality_pass=quality_pass,
                        )
                    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
                        # 整章扩写失败不阻塞章节生成
                        pass
                EVOLUTION_STORE.save(state)
                self._send_json(200, _evolution_payload(state, result, viewpoint_id))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/regenerate-chapter":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                state = EVOLUTION_STORE.load(project_id)
                if state is None:
                    self._send_json(404, {"error": "演化尚未开始"})
                    return
                viewpoint_id = str(payload.get("viewpoint_id") or "").strip()
                start_turn = int(payload.get("start_turn") or 0)
                end_turn = int(payload.get("end_turn") or 0)
                if start_turn < 1 or end_turn < start_turn:
                    self._send_json(400, {"error": "章节范围无效"})
                    return
                llm = _resolve_llm(payload.get("llm"))
                api_key = str(llm.get("api_key") or "").strip()
                if not api_key:
                    self._send_json(400, {"error": "重新生成本章需要 AI 通道"})
                    return
                global_guidance = str(payload.get("global_guidance") or "").strip()
                writing_style = str(payload.get("writing_style") or "").strip()
                style_card = str(payload.get("style_card") or "").strip()
                quality_pass = bool(payload.get("quality_pass") or False)
                event_turns = {event.turn for event in state.history}
                chapter_turns = sorted(
                    turn for turn in range(start_turn, end_turn + 1) if turn in event_turns
                )
                if not chapter_turns:
                    self._send_json(400, {"error": "该章节还没有可重写的回合"})
                    return
                variation = (
                    f"重新生成第{start_turn}–{end_turn}回合这一章：事件与事实保持不变，"
                    "换一种写法重写整章正文，保持人物语气与时间连续性。"
                )
                try:
                    _store_chapter_prose(
                        state,
                        start_turn,
                        end_turn,
                        viewpoint_id,
                        llm,
                        global_guidance,
                        variation,
                        writing_style=writing_style,
                        style_card=style_card,
                        quality_pass=quality_pass,
                    )
                except HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")[-300:]
                    self._send_json(502, {"error": f"AI 重写失败：{detail or exc}"})
                    return
                except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
                    self._send_json(502, {"error": f"AI 重写失败：{exc}"})
                    return
                EVOLUTION_STORE.save(state)
                self._send_json(200, _evolution_payload(state, viewpoint_id=viewpoint_id))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/guide":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                state = EVOLUTION_STORE.load(project_id)
                if state is None:
                    self._send_json(404, {"error": "演化尚未开始"})
                    return
                state.guidance = str(payload.get("guidance") or "").strip()
                EVOLUTION_STORE.save(state)
                self._send_json(
                    200,
                    _evolution_payload(state, viewpoint_id=str(payload.get("viewpoint_id") or "")),
                )
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/add-character":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                state = EVOLUTION_STORE.load(project_id)
                if state is None:
                    self._send_json(404, {"error": "演化尚未开始"})
                    return
                character = payload.get("character") or {}
                if not str(character.get("name") or character.get("title") or "").strip():
                    self._send_json(400, {"error": "角色姓名不能为空"})
                    return
                add_character_to_run(state, character)
                EVOLUTION_STORE.save(state)
                self._send_json(
                    200,
                    _evolution_payload(state, viewpoint_id=str(payload.get("viewpoint_id") or "")),
                )
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/reset":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                EVOLUTION_STORE.delete(project_id)
                self._send_json(200, {"ok": True})
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/projects/backup":
                payload = self._read_json_body()
                project = payload.get("project") or {}
                project_id = str(project.get("id") or "").strip()
                if not project_id:
                    raise ValueError("project id 不能为空")
                store_dir = EVOLUTION_STORE.directory
                store_dir.mkdir(parents=True, exist_ok=True)
                path = store_dir / f"{sanitize_project_id(project_id)}.project.json"
                temporary = path.with_suffix(".json.tmp")
                temporary.write_text(
                    json.dumps(
                        {"format": PROJECT_BACKUP_FORMAT, "project": project},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                os.replace(temporary, path)
                self._send_json(200, {"ok": True, "project_id": project_id})
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/projects/backups":
                rows: list[dict[str, Any]] = []
                store_dir = EVOLUTION_STORE.directory
                if store_dir.is_dir():
                    for path in sorted(store_dir.glob("*.project.json")):
                        try:
                            backup = json.loads(path.read_text(encoding="utf-8"))
                            project = backup.get("project") or {}
                            rows.append(
                                {
                                    "project_id": str(project.get("id") or ""),
                                    "name": str(project.get("name") or "未命名项目"),
                                    "updated_at": str(project.get("updated_at") or ""),
                                }
                            )
                        except (OSError, json.JSONDecodeError):
                            continue
                self._send_json(200, {"backups": rows})
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/projects/restore":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                store_dir = EVOLUTION_STORE.directory
                path = store_dir / f"{sanitize_project_id(project_id)}.project.json"
                if not path.is_file():
                    self._send_json(404, {"error": "没有找到该项目的磁盘备份"})
                    return
                backup = json.loads(path.read_text(encoding="utf-8"))
                project = backup.get("project") or {}
                if not str(project.get("id") or "").strip():
                    self._send_json(500, {"error": "备份文件损坏"})
                    return
                self._send_json(200, {"project": project})
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/projects":
                self._send_json(200, {"projects": _list_projects_meta()})
                return
            if self.command == "GET" and parsed_request.path.startswith("/lore-api/projects/"):
                project_id = parsed_request.path[len("/lore-api/projects/") :].strip("/")
                if project_id:
                    try:
                        project = _load_agent_project(project_id)
                    except KeyError as exc:
                        self._send_json(404, {"error": str(exc)})
                        return
                    self._send_json(200, {"project": project})
                    return
            if self.command == "POST" and parsed_request.path.startswith("/lore-api/projects/"):
                project_id = parsed_request.path[len("/lore-api/projects/") :].strip("/")
                payload = self._read_json_body()
                project = payload.get("project") if isinstance(payload.get("project"), dict) else payload
                if str(project.get("id") or "").strip() != project_id:
                    raise ValueError("project id 不匹配")
                _save_agent_project(project)
                self._send_json(200, {"ok": True, "project_id": project_id})
                return
        except subprocess.CalledProcessError as exc:
            self._send_json(
                500,
                {
                    "error": "Vault Web install failed",
                    "stdout": _tail_output(exc.stdout or ""),
                    "stderr": _tail_output(exc.stderr or ""),
                },
            )
            return
        except subprocess.TimeoutExpired as exc:
            self._send_json(
                500,
                {
                    "error": "Vault Web install timed out",
                    "stdout": _timeout_output(exc.stdout),
                    "stderr": _timeout_output(exc.stderr),
                },
            )
            return
        except OSError as exc:
            self._send_json(500, {"error": str(exc)})
            return
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
            return
        self._send_json(404, {"error": "not found"})

    def _proxy_to_vault(self) -> None:
        if self.command not in ALLOWED_METHODS:
            self._send_json(405, {"error": "method not allowed"})
            return

        parsed_request = urlparse(self.path)
        query = parse_qs(parsed_request.query)
        if parsed_request.path.startswith("/api/"):
            VAULT_MANAGER.ensure_default_core()
            base_url = VAULT_MANAGER.status()["base_url"]
            api_path = urlunparse(("", "", parsed_request.path, "", parsed_request.query, ""))
        else:
            base_url = (query.get("base_url") or [""])[0].strip()
            api_path = (query.get("path") or [""])[0].strip()
        if not _is_allowed_vault_url(base_url):
            self._send_json(
                400,
                {
                    "error": (
                        "base_url must point to localhost, 127.0.0.1, or ::1 "
                        "for the first Rhine-Lore milestone"
                    )
                },
            )
            return

        try:
            target = _join_base_and_path(base_url, api_path)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        body = self._read_body()
        headers = {"Accept": "application/json"}
        if body:
            headers["Content-Type"] = self.headers.get("Content-Type", "application/json")

        try:
            request = Request(target, data=body or None, headers=headers, method=self.command)
            with urlopen(request, timeout=15) as response:
                data = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "application/json")
        except HTTPError as exc:
            data = exc.read() or _json_bytes({"error": str(exc)})
            status = exc.code
            content_type = exc.headers.get("Content-Type", "application/json")
        except URLError as exc:
            self._send_json(502, {"error": f"Rhine-Vault request failed: {exc.reason}"})
            return

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def proxy_url(base_url: str, api_path: str) -> str:
    return "/vault-proxy?" + urlencode({"base_url": base_url, "path": api_path}, quote_via=quote)


def serve(host: str, port: int, web_root: Path) -> None:
    web_root = Path(web_root)
    if not web_root.exists():
        raise FileNotFoundError(f"web root does not exist: {web_root}")

    def handler(*args: Any, **kwargs: Any) -> RhineLoreHandler:
        return RhineLoreHandler(*args, directory=str(web_root), **kwargs)

    address = (host, port)
    httpd = ThreadingHTTPServer(address, handler)
    bind_any = host in {"0.0.0.0", "::", ""}
    url = f"http://127.0.0.1:{port}/" if bind_any else f"http://{host}:{port}/"
    vault_status = VAULT_MANAGER.ensure_default_core()
    print(f"Rhine-Lore is running at {url}")
    if bind_any:
        for lan_address in _lan_addresses():
            print(f"局域网访问: http://{lan_address}:{port}/")
        print("提示: 手机与电脑需在同一网络; 若无法访问, 请在 Windows 防火墙中放行 Python(专用网络)。")
    print(f"Serving UI from {web_root}")
    if vault_status["auto_start"]["error"]:
        print(f"Rhine-Vault Core auto-start skipped: {vault_status['auto_start']['error']}")
    else:
        print(f"Rhine-Vault Core target: {vault_status['base_url']}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nRhine-Lore stopped.")
    finally:
        VAULT_MANAGER.stop()
        httpd.server_close()


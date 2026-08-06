"""Small static server with a local Rhine-Vault proxy and launcher."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from rhine_lore.engine import (
    EvolutionState,
    EvolutionStore,
    TurnResult,
    advance,
    build_ai_prose_prompt,
    evolution_settings_from_dict,
    evolution_state_to_dict,
    render_novel,
    render_sandbox,
    start_run,
    turn_result_to_dict,
    viewpoint_options,
)


ALLOWED_PROXY_HOSTS = {"127.0.0.1", "localhost", "::1"}
ALLOWED_METHODS = {"GET", "POST", "PATCH"}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = PROJECT_ROOT / "data" / "projects"
DEFAULT_VAULT_HOST = "127.0.0.1"
DEFAULT_VAULT_PORT = 8795
DEFAULT_VAULT_PORT_CANDIDATES = (8795, 8796, 8797)
DEFAULT_VAULT_PORTS = set(DEFAULT_VAULT_PORT_CANDIDATES)
DEFAULT_VAULT_URL = f"http://{DEFAULT_VAULT_HOST}:{DEFAULT_VAULT_PORT}"
DEFAULT_VAULT_CHECKOUT = Path(__file__).resolve().parents[3] / "Rhine-Vault"
DEFAULT_VAULT_DATABASE = PROJECT_ROOT / "data" / "rhine-vault-core.db"
VAULT_WEB_INSTALL_TIMEOUT = 300
EVOLUTION_STORE = EvolutionStore(PROJECTS_DIR)


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
    return {
        "state": evolution_state_to_dict(state),
        "sandbox": render_sandbox(state),
        "novel": render_novel(state, viewpoint),
        "viewpoints": viewpoint_options(state),
        "result": turn_result_to_dict(result) if result else None,
        "message": result.message if result else "",
    }


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

    def do_GET(self) -> None:
        if self.path.startswith("/lore-api/"):
            self._handle_lore_api()
            return
        if self.path.startswith("/vault-proxy") or self.path.startswith("/api/"):
            self._proxy_to_vault()
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path.startswith("/lore-api/"):
            self._handle_lore_api()
            return
        if self.path.startswith("/vault-proxy") or self.path.startswith("/api/"):
            self._proxy_to_vault()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_PATCH(self) -> None:
        if self.path.startswith("/vault-proxy") or self.path.startswith("/api/"):
            self._proxy_to_vault()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
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

    def _vault_status_payload(self) -> dict[str, Any]:
        manager_status = VAULT_MANAGER.status()
        base_url = manager_status["base_url"] or DEFAULT_VAULT_URL
        return {
            "config": _default_vault_config(),
            "manager": manager_status,
            **_vault_health(base_url),
        }

    def _handle_lore_api(self) -> None:
        parsed_request = urlparse(self.path)
        try:
            if self.command == "GET" and parsed_request.path == "/lore-api/vault/status":
                self._send_json(200, self._vault_status_payload())
                return
            if self.command == "GET" and parsed_request.path == "/lore-api/vault/web/status":
                self._send_json(200, _vault_web_status(base_url=VAULT_MANAGER.status()["base_url"]))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/vault/web/install":
                payload = self._read_json_body()
                raw_path = str(payload.get("vault_path") or "").strip()
                vault_path = Path(raw_path) if raw_path else None
                self._send_json(200, _install_vault_web(vault_path))
                return
            if self.command == "POST" and parsed_request.path == "/lore-api/vault/connect":
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
                llm = payload.get("llm") or {}
                api_key = str(llm.get("api_key") or "").strip()
                if not api_key:
                    self._send_json(400, {"error": "未配置 API Key"})
                    return
                messages = build_ai_prose_prompt(state, viewpoint_id)
                chat_body = {
                    "workspace_id": "story-workspace",
                    "base_url": str(llm.get("base_url") or "").strip() or None,
                    "api_key": api_key,
                    "model": str(llm.get("model") or "").strip() or None,
                    "messages": messages,
                }
                vault_base = VAULT_MANAGER.status()["base_url"]
                try:
                    target = _join_base_and_path(vault_base, "/api/llm/openai-compatible/chat")
                    request = Request(
                        target,
                        data=json.dumps(chat_body, ensure_ascii=False).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urlopen(request, timeout=60) as response:
                        result = json.loads(response.read().decode("utf-8"))
                except HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")[-300:]
                    self._send_json(502, {"error": f"AI 生成失败：{detail or exc}"})
                    return
                except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                    self._send_json(502, {"error": f"AI 生成失败：{exc}"})
                    return
                text = str(result.get("answer") or "").strip()
                if not text:
                    self._send_json(502, {"error": "AI 返回为空"})
                    return
                latest_turn = state.history[-1].turn if state.history else state.turn
                prose_key = f"{latest_turn}:{viewpoint_id or (state.cast[0].id if state.cast else '')}"
                state.ai_prose[prose_key] = text
                min_turn = max(1, state.turn - 20)
                state.ai_prose = {
                    key: value
                    for key, value in state.ai_prose.items()
                    if int(key.split(":")[0]) >= min_turn
                }
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
            if self.command == "POST" and parsed_request.path == "/lore-api/evolution/reset":
                payload = self._read_json_body()
                project_id = str(payload.get("project_id") or "").strip()
                EVOLUTION_STORE.delete(project_id)
                self._send_json(200, {"ok": True})
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


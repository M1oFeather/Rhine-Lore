"""Embedded knowledge base for Rhine-Lore standalone mode.

Provides a local-only Rhine-Vault compatible API backed by a JSON file under
the data directory, so the Android/embedded build has a fully usable
knowledge base without requiring the external Rhine-Vault process.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class EmbeddedVaultStore:
    """Persistent local workspace/proposal/staging/node store."""

    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "embedded-vault.json"
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._data = {
                "workspaces": [
                    {
                        "workspace_id": "story-workspace",
                        "workspace_type": "project",
                        "display_name": "默认故事工作区",
                        "created_at": _now(),
                    }
                ],
                "nodes": [],
                "proposals": [],
                "staging": [],
            }
            self._save()
        else:
            self._data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            data = {}
        defaults = {
            "workspaces": [],
            "nodes": [],
            "proposals": [],
            "staging": [],
        }
        defaults.update({key: value for key, value in (data or {}).items() if isinstance(value, list)})
        return defaults

    def _save(self) -> None:
        tmp_path = self.path.with_suffix(".json.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)
        tmp_path.replace(self.path)

    # Workspaces -----------------------------------------------------------

    def workspaces(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._data["workspaces"]]

    def create_workspace(
        self,
        workspace_id: str,
        workspace_type: str = "project",
        display_name: str | None = None,
    ) -> dict[str, Any]:
        workspace_id = workspace_id.strip()
        if not workspace_id:
            raise ValueError("workspace_id 为空")
        with self._lock:
            for item in self._data["workspaces"]:
                if item["workspace_id"] == workspace_id:
                    return dict(item)
            workspace = {
                "workspace_id": workspace_id,
                "workspace_type": workspace_type if workspace_type in {"project", "library"} else "project",
                "display_name": display_name.strip() or workspace_id,
                "created_at": _now(),
            }
            self._data["workspaces"].append(workspace)
            self._save()
            return dict(workspace)

    def _ensure_workspace(self, workspace_id: str) -> dict[str, Any]:
        return self.create_workspace(workspace_id)

    # Proposals ------------------------------------------------------------

    def create_proposal(
        self,
        workspace_id: str,
        title: str,
        node_type: str,
        content: str,
        authority: str,
        tags: list[str],
    ) -> dict[str, Any]:
        with self._lock:
            self._ensure_workspace(workspace_id)
            temporary_id = _new_id("tmp")
            proposed_node = {
                "temporary_id": temporary_id,
                "title": title.strip(),
                "node_type": node_type.strip() or "Note",
                "content": content,
                "authority": authority.strip() or "experimental",
                "tags": list(tags or []),
                "created_at": _now(),
            }
            proposal = {
                "proposal_id": _new_id("prop"),
                "workspace_id": workspace_id,
                "title": title.strip(),
                "node_type": proposed_node["node_type"],
                "content": content,
                "authority": proposed_node["authority"],
                "tags": proposed_node["tags"],
                "proposed_nodes": [proposed_node],
                "status": "draft",
                "created_at": _now(),
            }
            self._data["proposals"].append(proposal)
            self._save()
            return dict(proposal)

    def proposals(self, workspace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._data["proposals"] if item["workspace_id"] == workspace_id]

    def stage_proposal(self, workspace_id: str, proposal_id: str, temporary_ids: list[str]) -> list[dict[str, Any]]:
        with self._lock:
            proposal = next(
                (item for item in self._data["proposals"] if item["proposal_id"] == proposal_id),
                None,
            )
            if proposal is None:
                raise KeyError(f"Proposal 不存在: {proposal_id}")
            wanted = set(temporary_ids or [])
            if not wanted:
                wanted = {node["temporary_id"] for node in proposal["proposed_nodes"]}
            for node in proposal["proposed_nodes"]:
                if node["temporary_id"] not in wanted:
                    continue
                if any(
                    entry["workspace_id"] == workspace_id
                    and entry["proposal_id"] == proposal_id
                    and entry.get("source_temporary_id") == node["temporary_id"]
                    for entry in self._data["staging"]
                ):
                    continue
                self._data["staging"].append(
                    {
                        "entry_id": _new_id("stage"),
                        "workspace_id": workspace_id,
                        "proposal_id": proposal_id,
                        "source_temporary_id": node["temporary_id"],
                        "title": node["title"],
                        "node_type": node["node_type"],
                        "content": node["content"],
                        "authority": node["authority"],
                        "tags": list(node["tags"]),
                        "status": "pending",
                        "created_at": _now(),
                    }
                )
            proposal["status"] = "staged"
            self._save()
            return [dict(item) for item in self._data["staging"] if item["workspace_id"] == workspace_id]

    # Staging --------------------------------------------------------------

    def staging(self, workspace_id: str, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = [item for item in self._data["staging"] if item["workspace_id"] == workspace_id]
            if status:
                rows = [item for item in rows if item.get("status") == status]
            return [dict(item) for item in rows]

    def approve_staging(self, workspace_id: str, entry_ids: list[str]) -> list[dict[str, Any]]:
        with self._lock:
            for entry in self._data["staging"]:
                if entry["workspace_id"] != workspace_id or entry["entry_id"] not in set(entry_ids or []):
                    continue
                if entry.get("status") == "approved":
                    continue
                entry["status"] = "approved"
                entry["approved_at"] = _now()
                self._data["nodes"].append(
                    {
                        "node_id": _new_id("node"),
                        "workspace_id": workspace_id,
                        "title": entry["title"],
                        "node_type": entry["node_type"],
                        "content": entry["content"],
                        "authority": entry["authority"],
                        "tags": list(entry["tags"]),
                        "source": "embedded-manual",
                        "created_at": entry.get("created_at") or _now(),
                        "updated_at": _now(),
                    }
                )
            self._save()
            return [dict(item) for item in self._data["staging"] if item["workspace_id"] == workspace_id]

    # Nodes ----------------------------------------------------------------

    def nodes(self, workspace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._data["nodes"] if item["workspace_id"] == workspace_id]

    def search(self, workspace_id: str, query: str, tags: list[str], result_limit: int) -> list[dict[str, Any]]:
        query = (query or "").strip().lower()
        wanted_tags = {tag.strip().lower() for tag in (tags or []) if tag.strip()}
        with self._lock:
            scored: list[tuple[float, dict[str, Any]]] = []
            for node in self._data["nodes"]:
                if node["workspace_id"] != workspace_id:
                    continue
                haystack = " ".join(
                    [
                        node.get("title") or "",
                        node.get("content") or "",
                        " ".join(node.get("tags") or []),
                    ]
                ).lower()
                score = 0.0
                if query:
                    score += (haystack.count(query) * 3) + (1.0 if query in (node.get("title") or "").lower() else 0.0)
                if wanted_tags:
                    node_tags = {tag.lower() for tag in node.get("tags") or []}
                    score += len(wanted_tags & node_tags) * 5
                if score > 0 or not query and not wanted_tags:
                    scored.append((score, node))
            scored.sort(key=lambda item: item[0], reverse=True)
            return [dict(node) for _, node in scored[: max(1, int(result_limit or 10))]]

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": "ok",
                "mode": "embedded",
                "workspace_count": len(self._data["workspaces"]),
                "node_count": len(self._data["nodes"]),
                "proposal_count": len(self._data["proposals"]),
                "staging_count": len(self._data["staging"]),
                "data_file": str(self.path),
            }

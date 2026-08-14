"""Embedded knowledge base for Rhine-Lore standalone mode.

Provides a local-only Rhine-Vault compatible API backed by a JSON file under
the data directory, so the Android/embedded build has a fully usable
knowledge base without requiring the external Rhine-Vault process.
"""

from __future__ import annotations

import copy
import hashlib
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


def _stable_node_id(workspace_id: str, title: str) -> str:
    digest = hashlib.sha256(title.strip().encode("utf-8")).hexdigest()[:10]
    return f"{workspace_id}.node-{digest}"


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
                "node_revisions": [],
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
            "node_revisions": [],
            "proposals": [],
            "staging": [],
        }
        defaults.update({key: value for key, value in (data or {}).items() if isinstance(value, list)})
        known_revisions = {
            (str(item.get("workspace_id") or ""), str(item.get("node_id") or ""), int(item.get("revision") or 1))
            for item in defaults["node_revisions"]
        }
        for node in defaults["nodes"]:
            node["revision"] = max(1, int(node.get("revision") or 1))
            node.setdefault("status", "active")
            node.setdefault("updated_at", node.get("created_at") or _now())
            key = (str(node.get("workspace_id") or ""), str(node.get("node_id") or ""), node["revision"])
            if key not in known_revisions:
                defaults["node_revisions"].append(self._revision_record(node, base_revision=None))
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
                "node_id": _stable_node_id(workspace_id, title),
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

    def update_proposed_node(
        self,
        workspace_id: str,
        proposal_id: str,
        temporary_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        allowed_fields = {"node_id", "title", "node_type", "content", "authority", "tags"}
        clean_patch = {key: value for key, value in patch.items() if key in allowed_fields}
        if not clean_patch:
            raise ValueError("没有可更新的资料字段")
        if "title" in clean_patch and not str(clean_patch["title"]).strip():
            raise ValueError("资料标题不能为空")
        if "content" in clean_patch and not str(clean_patch["content"]).strip():
            raise ValueError("资料内容不能为空")
        if "node_id" in clean_patch and not str(clean_patch["node_id"]).strip():
            raise ValueError("node_id 不能为空")
        if "tags" in clean_patch:
            clean_patch["tags"] = [str(item).strip() for item in clean_patch["tags"] if str(item).strip()]

        with self._lock:
            proposal = next(
                (
                    item
                    for item in self._data["proposals"]
                    if item["workspace_id"] == workspace_id and item["proposal_id"] == proposal_id
                ),
                None,
            )
            if proposal is None:
                raise KeyError(f"Proposal 不存在: {proposal_id}")
            if proposal.get("status") not in {"draft", "pending_review"}:
                raise ValueError("只有待整理的资料草稿可以编辑")
            node = next(
                (item for item in proposal["proposed_nodes"] if item["temporary_id"] == temporary_id),
                None,
            )
            if node is None:
                raise KeyError(f"候选资料不存在: {temporary_id}")
            node.update(clean_patch)
            if len(proposal["proposed_nodes"]) == 1:
                for key in allowed_fields:
                    if key in clean_patch:
                        proposal[key] = clean_patch[key]
            proposal["updated_at"] = _now()
            self._save()
            return dict(proposal)

    def reject_proposal(self, workspace_id: str, proposal_id: str) -> dict[str, Any]:
        with self._lock:
            proposal = next(
                (
                    item
                    for item in self._data["proposals"]
                    if item["workspace_id"] == workspace_id and item["proposal_id"] == proposal_id
                ),
                None,
            )
            if proposal is None:
                raise KeyError(f"Proposal 不存在: {proposal_id}")
            if proposal.get("status") == "staged":
                raise ValueError("已送审资料不能直接驳回")
            proposal["status"] = "rejected"
            proposal["rejected_at"] = _now()
            self._save()
            return dict(proposal)

    def stage_proposal(self, workspace_id: str, proposal_id: str, temporary_ids: list[str]) -> list[dict[str, Any]]:
        with self._lock:
            proposal = next(
                (item for item in self._data["proposals"] if item["proposal_id"] == proposal_id),
                None,
            )
            if proposal is None:
                raise KeyError(f"Proposal 不存在: {proposal_id}")
            if proposal.get("status") not in {"draft", "pending_review"}:
                raise ValueError("只有待整理的资料草稿可以送审")
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
                        "node_id": node["node_id"],
                        "title": node["title"],
                        "node_type": node["node_type"],
                        "content": node["content"],
                        "authority": node["authority"],
                        "tags": list(node["tags"]),
                        "proposed_node": copy.deepcopy(node),
                        "base_revision": self._node_revision(workspace_id, node["node_id"]),
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
            wanted = set(entry_ids or [])
            for entry in self._data["staging"]:
                if entry["workspace_id"] != workspace_id or entry["entry_id"] not in wanted:
                    continue
                if entry.get("status") == "approved":
                    continue
                node_id = str(entry.get("node_id") or _new_id("node"))
                current = self._find_node(workspace_id, node_id)
                base_revision = entry.get("base_revision")
                if current is not None and int(current.get("revision") or 1) != base_revision:
                    raise ValueError(f"资料已在送审后更新，请重新审核: {node_id}")
                if current is None and base_revision is not None:
                    raise ValueError(f"待更新资料已不存在，请重新审核: {node_id}")
                now = _now()
                next_revision = int(current.get("revision") or 0) + 1 if current is not None else 1
                node = {
                    "node_id": node_id,
                    "workspace_id": workspace_id,
                    "title": entry["title"],
                    "node_type": entry["node_type"],
                    "content": entry["content"],
                    "authority": entry["authority"],
                    "status": "active",
                    "tags": list(entry["tags"]),
                    "source": "embedded-manual",
                    "revision": next_revision,
                    "created_at": current.get("created_at") if current is not None else entry.get("created_at") or now,
                    "updated_at": now,
                }
                if current is None:
                    self._data["nodes"].append(node)
                else:
                    current.clear()
                    current.update(node)
                self._data["node_revisions"].append(
                    self._revision_record(node, base_revision=base_revision)
                )
                entry["status"] = "approved"
                entry["approved_at"] = now
            self._save()
            return [dict(item) for item in self._data["staging"] if item["workspace_id"] == workspace_id]

    # Nodes ----------------------------------------------------------------

    def nodes(self, workspace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._data["nodes"] if item["workspace_id"] == workspace_id]

    def node_revisions(self, workspace_id: str, node_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = [
                copy.deepcopy(item)
                for item in self._data["node_revisions"]
                if item["workspace_id"] == workspace_id and item["node_id"] == node_id
            ]
            return sorted(rows, key=lambda item: int(item.get("revision") or 0))

    def rollback_node(
        self,
        workspace_id: str,
        node_id: str,
        revision: int,
        actor_id: str = "human:lore",
    ) -> dict[str, Any]:
        with self._lock:
            current = self._find_node(workspace_id, node_id)
            if current is None:
                raise KeyError(f"资料不存在: {node_id}")
            target = next(
                (
                    item
                    for item in self._data["node_revisions"]
                    if item["workspace_id"] == workspace_id
                    and item["node_id"] == node_id
                    and int(item.get("revision") or 0) == int(revision)
                ),
                None,
            )
            if target is None:
                raise KeyError(f"资料版本不存在: {node_id} rev {revision}")
            base_revision = int(current.get("revision") or 1)
            restored = copy.deepcopy(target["node_snapshot"])
            restored.update(
                {
                    "node_id": node_id,
                    "workspace_id": workspace_id,
                    "revision": base_revision + 1,
                    "created_at": current.get("created_at") or restored.get("created_at") or _now(),
                    "updated_at": _now(),
                }
            )
            current.clear()
            current.update(restored)
            record = self._revision_record(restored, base_revision=base_revision, created_by=actor_id)
            record["restored_from_revision"] = int(revision)
            self._data["node_revisions"].append(record)
            self._save()
            return dict(restored)

    def _find_node(self, workspace_id: str, node_id: str) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self._data["nodes"]
                if item["workspace_id"] == workspace_id and item["node_id"] == node_id
            ),
            None,
        )

    def _node_revision(self, workspace_id: str, node_id: str) -> int | None:
        node = self._find_node(workspace_id, node_id)
        return None if node is None else int(node.get("revision") or 1)

    @staticmethod
    def _revision_record(
        node: dict[str, Any],
        base_revision: int | None,
        created_by: str = "human:lore",
    ) -> dict[str, Any]:
        return {
            "revision_id": _new_id("rev"),
            "workspace_id": node["workspace_id"],
            "node_id": node["node_id"],
            "revision": int(node.get("revision") or 1),
            "base_revision": base_revision,
            "changeset_id": None,
            "content_hash": hashlib.sha256(str(node.get("content") or "").encode("utf-8")).hexdigest(),
            "node_snapshot": copy.deepcopy(node),
            "markdown_path": None,
            "git_commit": None,
            "created_by": created_by,
            "created_at": node.get("updated_at") or _now(),
        }

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

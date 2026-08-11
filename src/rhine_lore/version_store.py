"""Git-like snapshot store for Rhine-Lore text content.

Each commit stores a full payload snapshot under
``<data>/versions/<kind>/<entity_id>/<timestamp>-<seq>.json`` so any project
or book can be rolled back to a previous state.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _now() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


class VersionStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "versions"
        self.root.mkdir(parents=True, exist_ok=True)

    def _entity_dir(self, kind: str, entity_id: str) -> Path:
        safe_kind = "".join(ch for ch in kind if ch.isalnum() or ch in "-_") or "misc"
        safe_id = "".join(ch for ch in entity_id if ch.isalnum() or ch in "-_.") or "entity"
        directory = self.root / safe_kind / safe_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def commit(
        self,
        kind: str,
        entity_id: str,
        message: str,
        payload: Any,
        char_count: int = 0,
    ) -> dict[str, Any]:
        directory = self._entity_dir(kind, entity_id)
        timestamp = _now()
        sequence = 0
        while True:
            snapshot_id = f"{timestamp}-{sequence:03d}"
            path = directory / f"{snapshot_id}.json"
            if not path.exists():
                break
            sequence += 1
        snapshot = {
            "snapshot_id": snapshot_id,
            "kind": kind,
            "entity_id": entity_id,
            "message": (message or "未命名版本").strip()[:200],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "char_count": int(char_count or 0),
        }
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {"format": "rhine-lore-version-v1", "snapshot": snapshot, "payload": payload},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
        return dict(snapshot)

    def history(self, kind: str, entity_id: str) -> list[dict[str, Any]]:
        directory = self._entity_dir(kind, entity_id)
        rows: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.json")):
            if path.name.endswith(".tmp"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                snapshot = data.get("snapshot") or {}
                rows.append(
                    {
                        "snapshot_id": str(snapshot.get("snapshot_id") or path.stem),
                        "kind": str(snapshot.get("kind") or kind),
                        "entity_id": str(snapshot.get("entity_id") or entity_id),
                        "message": str(snapshot.get("message") or "未命名版本"),
                        "created_at": str(snapshot.get("created_at") or ""),
                        "char_count": int(snapshot.get("char_count") or 0),
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(rows, key=lambda item: item["snapshot_id"], reverse=True)

    def load_snapshot(self, kind: str, entity_id: str, snapshot_id: str) -> dict[str, Any]:
        path = self._entity_dir(kind, entity_id) / f"{snapshot_id}.json"
        if not path.is_file():
            raise KeyError(f"快照不存在: {snapshot_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        snapshot = data.get("snapshot") or {}
        return {
            "snapshot": snapshot,
            "payload": data.get("payload"),
        }

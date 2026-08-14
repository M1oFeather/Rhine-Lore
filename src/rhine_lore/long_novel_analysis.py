"""Resumable hierarchical analysis for million-character novels.

The analyzer never sends an entire book to a model. It extracts structured
facts from chapter-local fragments, merges adjacent results through a bounded
tree, and persists every node by content hash. A changed chapter therefore
invalidates one leaf path instead of the whole book.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from rhine_lore.novel_store import BookStore


ANALYSIS_SCHEMA_VERSION = 2
AnalysisChat = Callable[[list[dict[str, str]]], str]
StatusCallback = Callable[[dict[str, Any]], None]

MODE_CONFIG: dict[str, dict[str, int | str]] = {
    "quick": {
        "label": "快速梳理",
        "fragment_chars": 16_000,
        "overlap_chars": 0,
        "group_size": 8,
    },
    "smart": {
        "label": "智能分析",
        "fragment_chars": 9_000,
        "overlap_chars": 240,
        "group_size": 6,
    },
    "deep": {
        "label": "逐段深读",
        "fragment_chars": 5_500,
        "overlap_chars": 360,
        "group_size": 5,
    },
}


class AnalysisCancelled(Exception):
    """Raised between model calls after a user requests cancellation."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "node"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _extract_json_object(text: str) -> dict[str, Any]:
    source = text.strip()
    if source.startswith("```"):
        source = re.sub(r"^```(?:json)?\s*|\s*```$", "", source, flags=re.IGNORECASE)
    try:
        payload = json.loads(source)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    start = source.find("{")
    end = source.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(source[start : end + 1])
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass
    raise ValueError("模型没有返回可读取的分析 JSON")


def _bounded_text(value: Any, limit: int = 600) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _source_chapters(value: Any, fallback: list[int]) -> list[int]:
    values = value if isinstance(value, list) else []
    chapters: set[int] = set()
    for item in values:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number > 0:
            chapters.add(number)
    if not chapters:
        chapters.update(number for number in fallback if number > 0)
    return sorted(chapters)


def _normalize_entity_list(
    value: Any,
    *,
    fallback_sources: list[int],
    kind: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in value if isinstance(value, list) else []:
        if not isinstance(raw, dict):
            continue
        name = _bounded_text(raw.get("name"), 120)
        if not name:
            continue
        row: dict[str, Any] = {
            "name": name,
            "notes": _bounded_text(raw.get("notes") or raw.get("state"), 900),
            "source_chapters": _source_chapters(raw.get("source_chapters"), fallback_sources),
        }
        if kind == "character":
            aliases = raw.get("aliases") if isinstance(raw.get("aliases"), list) else []
            row.update(
                {
                    "aliases": list(dict.fromkeys(_bounded_text(item, 80) for item in aliases if _bounded_text(item, 80))),
                    "role": _bounded_text(raw.get("role") or "角色", 80),
                    "first_chapter": int(raw.get("first_chapter") or min(row["source_chapters"], default=0)),
                    "last_chapter": int(raw.get("last_chapter") or max(row["source_chapters"], default=0)),
                }
            )
        else:
            row["type"] = _bounded_text(raw.get("type") or "设定", 80)
        rows.append(row)
    return rows


def _normalize_relations(value: Any, fallback_sources: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in value if isinstance(value, list) else []:
        if not isinstance(raw, dict):
            continue
        source = _bounded_text(raw.get("from"), 120)
        target = _bounded_text(raw.get("to"), 120)
        if not source or not target:
            continue
        rows.append(
            {
                "from": source,
                "to": target,
                "relation": _bounded_text(raw.get("relation") or "有关联", 240),
                "kind": _bounded_text(raw.get("kind") or "人物", 80),
                "source_chapters": _source_chapters(raw.get("source_chapters"), fallback_sources),
            }
        )
    return rows


def _normalize_note_list(value: Any, fallback_sources: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in value if isinstance(value, list) else []:
        if isinstance(raw, str):
            text = _bounded_text(raw, 800)
            sources = fallback_sources
        elif isinstance(raw, dict):
            text = _bounded_text(raw.get("text") or raw.get("thread") or raw.get("fact"), 800)
            sources = _source_chapters(raw.get("source_chapters"), fallback_sources)
        else:
            continue
        if text:
            rows.append({"text": text, "source_chapters": sorted(set(sources))})
    return rows


def normalize_analysis(value: Any, fallback_sources: list[int] | None = None) -> dict[str, Any]:
    """Normalize every model stage into the same stable, source-aware schema."""
    raw = value if isinstance(value, dict) else {}
    sources = fallback_sources or []
    timeline: list[dict[str, Any]] = []
    for item in raw.get("timeline") if isinstance(raw.get("timeline"), list) else []:
        if isinstance(item, str):
            title = _bounded_text(item, 180)
            summary = title
            item_sources = sources
            participants: list[str] = []
        elif isinstance(item, dict):
            title = _bounded_text(item.get("title") or item.get("event"), 180)
            summary = _bounded_text(item.get("summary") or item.get("description") or title, 800)
            item_sources = _source_chapters(item.get("source_chapters"), sources)
            participants = [
                _bounded_text(name, 100)
                for name in (item.get("participants") if isinstance(item.get("participants"), list) else [])
                if _bounded_text(name, 100)
            ]
        else:
            continue
        if title or summary:
            timeline.append(
                {
                    "title": title or summary[:80],
                    "summary": summary,
                    "participants": list(dict.fromkeys(participants)),
                    "source_chapters": sorted(set(item_sources)),
                }
            )
    return {
        "source_chapters": _source_chapters(raw.get("source_chapters"), sources),
        "summary": _bounded_text(raw.get("summary"), 2_400),
        "characters": _normalize_entity_list(
            raw.get("characters"), fallback_sources=sources, kind="character"
        ),
        "settings": _normalize_entity_list(
            raw.get("settings"), fallback_sources=sources, kind="setting"
        ),
        "relations": _normalize_relations(raw.get("relations"), sources),
        "timeline": timeline,
        "key_facts": _normalize_note_list(raw.get("key_facts"), sources),
        "unresolved_threads": _normalize_note_list(raw.get("unresolved_threads"), sources),
        "resolved_threads": _normalize_note_list(raw.get("resolved_threads"), sources),
    }


def _split_fragment_ranges(text: str, max_chars: int, overlap: int) -> list[tuple[int, int]]:
    if not text:
        return [(0, 0)]
    if len(text) <= max_chars:
        return [(0, len(text))]
    ranges: list[tuple[int, int]] = []
    start = 0
    minimum = max(1, int(max_chars * 0.62))
    while start < len(text):
        hard_end = min(len(text), start + max_chars)
        end = hard_end
        if hard_end < len(text):
            window_start = min(hard_end, start + minimum)
            candidates = [
                text.rfind("\n\n", window_start, hard_end),
                text.rfind("\n", window_start, hard_end),
                max(text.rfind(mark, window_start, hard_end) for mark in "。！？!?；;"),
            ]
            boundary = max(candidates)
            if boundary >= window_start:
                end = boundary + (2 if text[boundary : boundary + 2] == "\n\n" else 1)
        if end <= start:
            end = hard_end
        ranges.append((start, end))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return ranges


def _merge_call_count(unit_count: int, group_size: int) -> int:
    calls = 0
    count = unit_count
    while count > 1:
        full, remainder = divmod(count, group_size)
        calls += full + (1 if remainder > 1 else 0)
        count = full + (1 if remainder else 0)
    return calls


def _dedupe_rows(rows: list[dict[str, Any]], key_fn: Callable[[dict[str, Any]], str]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = key_fn(row).casefold().strip()
        if not key:
            continue
        if key not in merged:
            merged[key] = dict(row)
            continue
        current = merged[key]
        current["source_chapters"] = sorted(
            set(current.get("source_chapters") or []) | set(row.get("source_chapters") or [])
        )
        if len(str(row.get("notes") or "")) > len(str(current.get("notes") or "")):
            current["notes"] = row.get("notes")
        if "aliases" in current:
            current["aliases"] = list(
                dict.fromkeys((current.get("aliases") or []) + (row.get("aliases") or []))
            )
        if "first_chapter" in current:
            positive = [
                int(number)
                for number in (current.get("first_chapter"), row.get("first_chapter"))
                if int(number or 0) > 0
            ]
            current["first_chapter"] = min(positive, default=0)
            current["last_chapter"] = max(
                int(current.get("last_chapter") or 0), int(row.get("last_chapter") or 0)
            )
    return list(merged.values())


def _root_alias_map(characters: list[dict[str, Any]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item in characters:
        canonical = str(item.get("name") or "").casefold()
        if not canonical:
            continue
        aliases[canonical] = canonical
        for alias in item.get("aliases") or []:
            aliases[str(alias).casefold()] = canonical
    return aliases


def _compose_final_analysis(
    root: dict[str, Any],
    leaves: list[dict[str, Any]],
    *,
    book: dict[str, Any],
    mode: str,
    plan: dict[str, Any],
    cached_steps: int,
) -> dict[str, Any]:
    """Keep the hierarchy's editorial conclusions and the leaves' full registry."""
    root = normalize_analysis(root)
    leaf_characters = [item for leaf in leaves for item in leaf.get("characters") or []]
    alias_map = _root_alias_map(root["characters"])

    def character_key(item: dict[str, Any]) -> str:
        name = str(item.get("name") or "").casefold()
        return alias_map.get(name, name)

    characters = _dedupe_rows(root["characters"] + leaf_characters, character_key)
    characters.sort(key=lambda item: (int(item.get("first_chapter") or 10**9), str(item.get("name") or "")))
    settings = _dedupe_rows(
        root["settings"] + [item for leaf in leaves for item in leaf.get("settings") or []],
        lambda item: str(item.get("name") or ""),
    )
    relations = _dedupe_rows(
        root["relations"] + [item for leaf in leaves for item in leaf.get("relations") or []],
        lambda item: "|".join(
            str(item.get(key) or "") for key in ("from", "to", "relation", "kind")
        ),
    )
    timeline = _dedupe_rows(
        [item for leaf in leaves for item in leaf.get("timeline") or []] + root["timeline"],
        lambda item: str(item.get("title") or item.get("summary") or ""),
    )
    timeline.sort(key=lambda item: min(item.get("source_chapters") or [10**9]))
    key_facts = _dedupe_rows(
        root["key_facts"] + [item for leaf in leaves for item in leaf.get("key_facts") or []],
        lambda item: str(item.get("text") or ""),
    )
    unresolved = root["unresolved_threads"]
    if not unresolved:
        unresolved = _dedupe_rows(
            [item for leaf in leaves for item in leaf.get("unresolved_threads") or []],
            lambda item: str(item.get("text") or ""),
        )
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "summary": root["summary"] or str(book.get("summary") or ""),
        "characters": characters,
        "settings": settings,
        "relations": relations,
        "timeline": timeline,
        "key_facts": key_facts,
        "unresolved_threads": unresolved,
        "resolved_threads": root["resolved_threads"],
        "offline": False,
        "updated_at": _now(),
        "coverage": {
            "chapters_analyzed": int(plan["chapter_count"]),
            "chapters_total": int(plan["chapter_count"]),
            "characters_analyzed": int(plan["total_chars"]),
            "characters_total": int(plan["total_chars"]),
            "percent": 100,
        },
        "analysis_meta": {
            "mode": mode,
            "fragments": int(plan["fragment_count"]),
            "model_requests": int(plan["estimated_requests"] - cached_steps),
            "cache_hits": int(cached_steps),
            "schema_version": ANALYSIS_SCHEMA_VERSION,
        },
    }


class LongNovelAnalyzer:
    """Plan and execute a persistent map-reduce analysis for one book store."""

    def __init__(self, store: BookStore):
        self.store = store

    def _root(self, book_id: str) -> Path:
        return self.store.analysis_directory(book_id) / f"v{ANALYSIS_SCHEMA_VERSION}"

    def status_path(self, book_id: str) -> Path:
        return self._root(book_id) / "status.json"

    def read_status(self, book_id: str) -> dict[str, Any] | None:
        return _read_json(self.status_path(book_id))

    def write_status(self, book_id: str, status: dict[str, Any]) -> dict[str, Any]:
        status["updated_at"] = _now()
        _atomic_json(self.status_path(book_id), status)
        return status

    def plan(self, book_id: str, mode: str = "smart") -> dict[str, Any]:
        if mode not in MODE_CONFIG:
            raise ValueError("分析模式无效")
        config = MODE_CONFIG[mode]
        book = self.store.get_book(book_id)
        units: list[dict[str, Any]] = []
        long_chapters = 0
        for chapter_meta in book.get("chapters") or []:
            chapter = self.store.get_chapter(book_id, str(chapter_meta.get("id") or ""))
            content = str(chapter.get("content") or "")
            ranges = _split_fragment_ranges(
                content,
                int(config["fragment_chars"]),
                int(config["overlap_chars"]),
            )
            if len(ranges) > 1:
                long_chapters += 1
            for fragment_index, (start, end) in enumerate(ranges, start=1):
                fragment = content[start:end]
                source_hash = _digest(
                    json.dumps(
                        {
                            "schema": ANALYSIS_SCHEMA_VERSION,
                            "mode": mode,
                            "chapter_id": chapter["id"],
                            "title": chapter["title"],
                            "order": chapter["order"],
                            "fragment": fragment_index,
                            "start": start,
                            "end": end,
                            "content": fragment,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                units.append(
                    {
                        "unit_id": f"{chapter['id']}-{fragment_index}",
                        "chapter_id": chapter["id"],
                        "chapter_title": chapter["title"],
                        "chapter_order": int(chapter["order"]),
                        "fragment_index": fragment_index,
                        "fragment_count": len(ranges),
                        "start": start,
                        "end": end,
                        "content": fragment,
                        "source_hash": source_hash,
                    }
                )
        group_size = int(config["group_size"])
        merge_calls = _merge_call_count(len(units), group_size)
        return {
            "book_id": book_id,
            "book": book,
            "mode": mode,
            "mode_label": str(config["label"]),
            "chapter_count": len(book.get("chapters") or []),
            "total_chars": int(book.get("total_chars") or 0),
            "fragment_count": len(units),
            "long_chapters": long_chapters,
            "max_fragment_chars": int(config["fragment_chars"]),
            "group_size": group_size,
            "merge_calls": merge_calls,
            "estimated_requests": len(units) + merge_calls,
            "units": units,
        }

    @staticmethod
    def public_plan(plan: dict[str, Any]) -> dict[str, Any]:
        return {
            key: plan[key]
            for key in (
                "mode",
                "mode_label",
                "chapter_count",
                "total_chars",
                "fragment_count",
                "long_chapters",
                "max_fragment_chars",
                "merge_calls",
                "estimated_requests",
            )
        }

    def _unit_path(self, book_id: str, mode: str, unit_id: str) -> Path:
        return self._root(book_id) / "units" / mode / f"{_safe_name(unit_id)}.json"

    def _group_path(self, book_id: str, mode: str, level: int, index: int) -> Path:
        return self._root(book_id) / "groups" / mode / f"level-{level}-group-{index}.json"

    @staticmethod
    def _leaf_messages(book: dict[str, Any], unit: dict[str, Any]) -> list[dict[str, str]]:
        system = (
            "你是长篇小说档案编辑。只依据给出的正文提取信息，保持人名原写法，"
            "不猜测未出现的设定。所有 source_chapters 都填写当前章节号。"
        )
        body = unit["content"] or "（本单元是卷名或章节标题页，没有正文）"
        user = f"""作品：《{book.get('name') or '未命名'}》
类型：{book.get('genre') or '未分类'}
章节：第 {unit['chapter_order']} 项《{unit['chapter_title']}》
片段：{unit['fragment_index']} / {unit['fragment_count']}，字符 {unit['start']} - {unit['end']}

正文：
{body}

输出一个 JSON 对象，不要代码块：
{{
  "source_chapters":[{unit['chapter_order']}],
  "summary":"本片段发生了什么，以及叙事状态如何变化",
  "characters":[{{"name":"姓名","aliases":[],"role":"本段身份或作用","notes":"动机、状态、变化","first_chapter":{unit['chapter_order']},"last_chapter":{unit['chapter_order']},"source_chapters":[{unit['chapter_order']}]}}],
  "settings":[{{"name":"地点、势力、物品或规则","type":"地点/势力/物品/规则","notes":"原文可确认的信息","source_chapters":[{unit['chapter_order']}]}}],
  "relations":[{{"from":"实体","to":"实体","relation":"关系或变化","kind":"人物/势力/地点","source_chapters":[{unit['chapter_order']}]}}],
  "timeline":[{{"title":"事件短标题","summary":"事件、原因和结果","participants":[],"source_chapters":[{unit['chapter_order']}]}}],
  "key_facts":[{{"text":"影响后文的一条事实","source_chapters":[{unit['chapter_order']}]}}],
  "unresolved_threads":[{{"text":"本段新产生或仍未解释的悬念","source_chapters":[{unit['chapter_order']}]}}],
  "resolved_threads":[{{"text":"本段明确回收的悬念及答案","source_chapters":[{unit['chapter_order']}]}}]
}}
空数组优于臆造。摘要不超过 220 字。"""
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    @staticmethod
    def _compact_child(child: dict[str, Any]) -> dict[str, Any]:
        compact = {
            "source_chapters": child.get("source_chapters") or [],
            "summary": _bounded_text(child.get("summary"), 900),
            "characters": (child.get("characters") or [])[:28],
            "settings": (child.get("settings") or [])[:24],
            "relations": (child.get("relations") or [])[:36],
            "timeline": (child.get("timeline") or [])[:32],
            "key_facts": (child.get("key_facts") or [])[:28],
            "unresolved_threads": (child.get("unresolved_threads") or [])[:24],
            "resolved_threads": (child.get("resolved_threads") or [])[:24],
        }
        encoded = json.dumps(compact, ensure_ascii=False)
        if len(encoded) <= 18_000:
            return compact
        return {
            "source_chapters": compact["source_chapters"],
            "summary": compact["summary"],
            "characters": compact["characters"][:14],
            "settings": compact["settings"][:12],
            "relations": compact["relations"][:18],
            "timeline": compact["timeline"][:16],
            "key_facts": compact["key_facts"][:14],
            "unresolved_threads": compact["unresolved_threads"][:12],
            "resolved_threads": compact["resolved_threads"][:12],
        }

    @classmethod
    def _merge_messages(
        cls,
        book: dict[str, Any],
        children: list[dict[str, Any]],
        level: int,
    ) -> list[dict[str, str]]:
        sources = sorted(
            {chapter for child in children for chapter in child.get("source_chapters") or []}
        )
        payload = json.dumps([cls._compact_child(child) for child in children], ensure_ascii=False)
        system = (
            "你是长篇小说的结构编辑。按原有时间顺序归并相邻分析，消除同一实体的重复项，"
            "识别别名与状态变化；若后文明确解释了旧伏笔，把它移到 resolved_threads。"
            "不得丢失 source_chapters，也不得补写原文之外的剧情。"
        )
        user = f"""作品：《{book.get('name') or '未命名'}》
归并层级：{level}
覆盖章节：{sources[0] if sources else 0} - {sources[-1] if sources else 0}

相邻分析节点 JSON：
{payload}

请输出与输入节点相同字段的单个 JSON 对象。要求：
1. 顶层 source_chapters 保留全部覆盖章节，summary 概括这一连续区间的因果推进，不超过 500 字。
2. 合并角色别名，保留 first_chapter、last_chapter 和每项的全部 source_chapters。
3. timeline 保持先后顺序，合并重复事件但不打乱因果。
4. 区分“仍未解释”和“已经回收”的伏笔。
5. 重要信息优先，空数组优于臆造。"""
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    @staticmethod
    def _call_model(
        chat: AnalysisChat,
        messages: list[dict[str, str]],
        cancel: threading.Event,
        attempts: int = 3,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(attempts):
            if cancel.is_set():
                raise AnalysisCancelled()
            try:
                return _extract_json_object(chat(messages))
            except AnalysisCancelled:
                raise
            except Exception as exc:  # noqa: BLE001 - retry transport and malformed model output
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                if cancel.wait(min(8.0, 1.5 * (2**attempt))):
                    raise AnalysisCancelled() from exc
        raise ValueError(f"分析节点连续失败 {attempts} 次：{last_error}") from last_error

    def run(
        self,
        book_id: str,
        chat: AnalysisChat,
        *,
        mode: str = "smart",
        force: bool = False,
        cancel_event: threading.Event | None = None,
        status: dict[str, Any] | None = None,
        status_callback: StatusCallback | None = None,
    ) -> dict[str, Any]:
        cancel = cancel_event or threading.Event()
        plan = self.plan(book_id, mode)
        public_plan = self.public_plan(plan)
        total_steps = max(1, int(plan["estimated_requests"]))
        state = status or {
            "job_id": f"analysis-{uuid.uuid4().hex[:12]}",
            "book_id": book_id,
            "state": "running",
            "mode": mode,
            "offline": False,
            "started_at": _now(),
        }
        state.update(
            {
                "state": "running",
                "stage": "extracting",
                "message": "正在逐章建立可追溯档案",
                "progress": 0,
                "completed_steps": 0,
                "total_steps": total_steps,
                "cached_steps": 0,
                "processed_fragments": 0,
                "total_fragments": int(plan["fragment_count"]),
                "current_chapter": "",
                "current_order": 0,
                "can_resume": True,
                "plan": public_plan,
            }
        )

        def update(**values: Any) -> None:
            state.update(values)
            state["progress"] = min(
                99,
                round((int(state.get("completed_steps") or 0) / total_steps) * 100),
            )
            self.write_status(book_id, state)
            if status_callback:
                status_callback(dict(state))

        update()
        leaves: list[dict[str, Any]] = []
        try:
            for unit in plan["units"]:
                if cancel.is_set():
                    raise AnalysisCancelled()
                update(
                    current_chapter=unit["chapter_title"],
                    current_order=unit["chapter_order"],
                    message=f"正在阅读第 {unit['chapter_order']} 项《{unit['chapter_title']}》",
                )
                path = self._unit_path(book_id, mode, unit["unit_id"])
                cached = None if force else _read_json(path)
                if cached and cached.get("source_hash") == unit["source_hash"]:
                    result = normalize_analysis(cached.get("result"), [unit["chapter_order"]])
                    state["cached_steps"] = int(state.get("cached_steps") or 0) + 1
                else:
                    raw = self._call_model(
                        chat,
                        self._leaf_messages(plan["book"], unit),
                        cancel,
                    )
                    result = normalize_analysis(raw, [unit["chapter_order"]])
                    _atomic_json(
                        path,
                        {
                            "schema_version": ANALYSIS_SCHEMA_VERSION,
                            "source_hash": unit["source_hash"],
                            "chapter_id": unit["chapter_id"],
                            "chapter_order": unit["chapter_order"],
                            "fragment_index": unit["fragment_index"],
                            "result": result,
                            "updated_at": _now(),
                        },
                    )
                leaves.append(result)
                update(
                    completed_steps=int(state.get("completed_steps") or 0) + 1,
                    processed_fragments=int(state.get("processed_fragments") or 0) + 1,
                )

            current = leaves
            level = 1
            while len(current) > 1:
                next_level: list[dict[str, Any]] = []
                groups = [current[index : index + int(plan["group_size"])] for index in range(0, len(current), int(plan["group_size"]))]
                for group_index, children in enumerate(groups, start=1):
                    if cancel.is_set():
                        raise AnalysisCancelled()
                    if len(children) == 1:
                        next_level.append(children[0])
                        continue
                    sources = sorted(
                        {
                            chapter
                            for child in children
                            for chapter in child.get("source_chapters") or []
                        }
                    )
                    update(
                        stage="merging",
                        current_chapter="",
                        current_order=sources[0] if sources else 0,
                        message=(
                            f"正在归并第 {sources[0]} - {sources[-1]} 项"
                            if sources
                            else f"正在归并第 {level} 层"
                        ),
                    )
                    input_hash = _digest(
                        json.dumps(children, ensure_ascii=False, sort_keys=True)
                        + f"|{mode}|{level}|{ANALYSIS_SCHEMA_VERSION}"
                    )
                    path = self._group_path(book_id, mode, level, group_index)
                    cached = None if force else _read_json(path)
                    if cached and cached.get("input_hash") == input_hash:
                        result = normalize_analysis(cached.get("result"), sources)
                        state["cached_steps"] = int(state.get("cached_steps") or 0) + 1
                    else:
                        raw = self._call_model(
                            chat,
                            self._merge_messages(plan["book"], children, level),
                            cancel,
                        )
                        result = normalize_analysis(raw, sources)
                        _atomic_json(
                            path,
                            {
                                "schema_version": ANALYSIS_SCHEMA_VERSION,
                                "input_hash": input_hash,
                                "level": level,
                                "group": group_index,
                                "result": result,
                                "updated_at": _now(),
                            },
                        )
                    next_level.append(result)
                    update(completed_steps=int(state.get("completed_steps") or 0) + 1)
                current = next_level
                level += 1

            update(stage="finalizing", message="正在整理人物、时间线与伏笔档案")
            root = current[0] if current else normalize_analysis({})
            final = _compose_final_analysis(
                root,
                leaves,
                book=plan["book"],
                mode=mode,
                plan=plan,
                cached_steps=int(state.get("cached_steps") or 0),
            )
            self.store.save_analysis(book_id, final)
            state.update(
                {
                    "state": "completed",
                    "stage": "completed",
                    "message": "全书档案已建立",
                    "progress": 100,
                    "completed_steps": total_steps,
                    "current_chapter": "",
                    "current_order": 0,
                    "can_resume": False,
                    "completed_at": _now(),
                    "result_summary": {
                        "characters": len(final["characters"]),
                        "settings": len(final["settings"]),
                        "relations": len(final["relations"]),
                        "timeline": len(final["timeline"]),
                        "unresolved_threads": len(final["unresolved_threads"]),
                    },
                }
            )
            self.write_status(book_id, state)
            if status_callback:
                status_callback(dict(state))
            return final
        except AnalysisCancelled:
            state.update(
                {
                    "state": "cancelled",
                    "stage": "paused",
                    "message": "分析已暂停，已完成内容会保留",
                    "can_resume": True,
                    "completed_at": _now(),
                }
            )
            self.write_status(book_id, state)
            if status_callback:
                status_callback(dict(state))
            raise
        except Exception as exc:
            state.update(
                {
                    "state": "failed",
                    "stage": "paused",
                    "message": "分析遇到问题，稍后可从缓存继续",
                    "error": _bounded_text(exc, 500),
                    "can_resume": True,
                    "completed_at": _now(),
                }
            )
            self.write_status(book_id, state)
            if status_callback:
                status_callback(dict(state))
            raise


class AnalysisTaskManager:
    """Own background workers while keeping task truth persisted per book."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tasks: dict[str, dict[str, Any]] = {}

    def preview(self, store: BookStore, book_id: str, mode: str = "smart") -> dict[str, Any]:
        analyzer = LongNovelAnalyzer(store)
        return analyzer.public_plan(analyzer.plan(book_id, mode))

    def status(self, store: BookStore, book_id: str) -> dict[str, Any]:
        analyzer = LongNovelAnalyzer(store)
        status = analyzer.read_status(book_id)
        if status is None:
            return {
                "book_id": book_id,
                "state": "idle",
                "stage": "idle",
                "message": "尚未建立全书档案",
                "progress": 0,
                "can_resume": False,
            }
        with self._lock:
            runtime = self._tasks.get(book_id)
            alive = bool(runtime and runtime["thread"].is_alive())
        if status.get("state") in {"queued", "running"} and not alive:
            status.update(
                {
                    "state": "paused",
                    "stage": "paused",
                    "message": "上次分析已中断，可以从已完成部分继续",
                    "can_resume": True,
                }
            )
            analyzer.write_status(book_id, status)
        return status

    def start(
        self,
        store: BookStore,
        book_id: str,
        *,
        mode: str,
        force: bool,
        chat: AnalysisChat | None,
    ) -> dict[str, Any]:
        analyzer = LongNovelAnalyzer(store)
        plan = analyzer.plan(book_id, mode)
        with self._lock:
            existing = self._tasks.get(book_id)
            if existing and existing["thread"].is_alive():
                return self.status(store, book_id)
            cancel = threading.Event()
            status = {
                "job_id": f"analysis-{uuid.uuid4().hex[:12]}",
                "book_id": book_id,
                "state": "queued",
                "stage": "preparing",
                "message": "正在准备全书档案",
                "mode": mode,
                "offline": chat is None,
                "progress": 0,
                "completed_steps": 0,
                "total_steps": max(1, int(plan["estimated_requests"])),
                "cached_steps": 0,
                "processed_fragments": 0,
                "total_fragments": int(plan["fragment_count"]),
                "can_resume": True,
                "plan": analyzer.public_plan(plan),
                "started_at": _now(),
            }
            analyzer.write_status(book_id, status)

            def worker() -> None:
                try:
                    if chat is None:
                        heuristic = store.heuristic_analysis(book_id)
                        heuristic.update(
                            {
                                "schema_version": ANALYSIS_SCHEMA_VERSION,
                                "summary": str(plan["book"].get("summary") or ""),
                                "timeline": [],
                                "resolved_threads": [],
                                "offline": True,
                                "updated_at": _now(),
                                "coverage": {
                                    "chapters_analyzed": int(plan["chapter_count"]),
                                    "chapters_total": int(plan["chapter_count"]),
                                    "characters_analyzed": int(plan["total_chars"]),
                                    "characters_total": int(plan["total_chars"]),
                                    "percent": 100,
                                },
                                "analysis_meta": {
                                    "mode": "local-index",
                                    "fragments": 0,
                                    "model_requests": 0,
                                    "cache_hits": 0,
                                    "schema_version": ANALYSIS_SCHEMA_VERSION,
                                },
                            }
                        )
                        store.save_analysis(book_id, heuristic)
                        status.update(
                            {
                                "state": "completed",
                                "stage": "completed",
                                "message": "基础索引已建立，连接 AI 后可进行全文深读",
                                "progress": 100,
                                "completed_steps": status["total_steps"],
                                "can_resume": False,
                                "completed_at": _now(),
                                "result_summary": {
                                    "characters": len(heuristic.get("characters") or []),
                                    "settings": 0,
                                    "relations": 0,
                                    "timeline": 0,
                                    "unresolved_threads": 0,
                                },
                            }
                        )
                        analyzer.write_status(book_id, status)
                    else:
                        analyzer.run(
                            book_id,
                            chat,
                            mode=mode,
                            force=force,
                            cancel_event=cancel,
                            status=status,
                        )
                except AnalysisCancelled:
                    pass
                except Exception:
                    # LongNovelAnalyzer has already persisted a resumable failure.
                    pass
                finally:
                    with self._lock:
                        current = self._tasks.get(book_id)
                        if current and current.get("cancel") is cancel:
                            self._tasks.pop(book_id, None)

            thread = threading.Thread(
                target=worker,
                name=f"lore-analysis-{book_id[-8:]}",
                daemon=True,
            )
            self._tasks[book_id] = {"thread": thread, "cancel": cancel}
            thread.start()
        return status

    def cancel(self, store: BookStore, book_id: str) -> dict[str, Any]:
        with self._lock:
            runtime = self._tasks.get(book_id)
            if runtime and runtime["thread"].is_alive():
                runtime["cancel"].set()
        status = self.status(store, book_id)
        if status.get("state") in {"queued", "running"}:
            status["cancel_requested"] = True
            status["message"] = "将在当前分析片段完成后暂停"
            LongNovelAnalyzer(store).write_status(book_id, status)
        return status

    def wait(self, book_id: str, timeout: float = 5.0) -> bool:
        with self._lock:
            runtime = self._tasks.get(book_id)
            thread = runtime.get("thread") if runtime else None
        if thread:
            thread.join(timeout)
            return not thread.is_alive()
        return True

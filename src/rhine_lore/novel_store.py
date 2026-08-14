"""Chapter-split long-novel storage for Rhine-Lore.

Each imported book lives under ``<data>/books/<book_id>/``:

- ``book.json``: metadata + per-chapter summary cache (small, always loaded)
- ``chapters.json``: chapter index (id/title/order/char_count)
- ``chapters/<chapter_id>.txt``: one file per chapter (content loaded lazily)

This keeps multi-million-character novels usable: the API and AI context only
ever touch metadata, summaries, and a single chapter at a time.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return cleaned or f"book-{uuid.uuid4().hex[:8]}"


_CHAPTER_HEADER = re.compile(
    r"^\s*(?:"
    r"第\s*[0-9〇零一二三四五六七八九十百千万两]+\s*[章回节卷部].*"
    r"|(?:Chapter|CHAPTER|CHAP)\s+\d+.*"
    r"|(?:卷[0-9〇零一二三四五六七八九十百千万两首]+|[上中下终序]卷|序章|楔子|引子|序幕|前言|尾声|后记|番外|终章|大结局).*"
    r")\s*$"
)

_NAMED_ACTION = re.compile(r"([\u4e00-\u9fa5]{2,4})(?:说|道|问|喊|叫|笑|叹|答|想|看|走|来|去)")
_ENGLISH_NAME = re.compile(r"\b[A-Z][a-z]{2,}\b")
_STOPWORDS = {
    "我们", "他们", "她们", "你们", "自己", "这个", "那个", "什么", "没有",
    "已经", "现在", "时候", "知道", "一个", "可以", "只是", "但是", "于是",
    "因为", "所以", "还是", "就是", "不是", "如果", "虽然", "然后", "突然",
    "忽然", "这时", "那时", "只见", "便是", "心中", "脸上", "眼里", "身上",
}


def split_txt_chapters(text: str, max_chunk_chars: int = 4200) -> list[dict[str, str]]:
    """Split raw TXT into chapters.

    Prefers real chapter headings; falls back to paragraph-chunk splitting so
    plain-text exports without headings still become readable chapters.
    """
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    chapters: list[dict[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        content = "\n".join(current_lines).strip()
        if content or current_title:
            chapters.append({"title": current_title or f"第{len(chapters) + 1}节", "content": content})
        current_title = ""
        current_lines = []

    for line in lines:
        stripped = line.strip()
        if _CHAPTER_HEADER.match(stripped):
            flush()
            current_title = stripped
            continue
        current_lines.append(line)
        if not current_title and len("\n".join(current_lines)) >= max_chunk_chars:
            flush()
    flush()

    if not chapters:
        return [{"title": "第1节", "content": text.strip()}]

    if len(chapters) == 1:
        # No real headings found: split the single body into readable chunks.
        body = chapters[0]["content"]
        if len(body) > max_chunk_chars:
            chunks = _chunk_plain_text(body, max_chunk_chars)
            return [
                {"title": f"第{index + 1}节", "content": chunk}
                for index, chunk in enumerate(chunks)
                if chunk.strip()
            ]
    return chapters


def _chunk_plain_text(body: str, max_chars: int) -> list[str]:
    """Split a heading-less body into bounded chunks at sentence/paragraph edges."""
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", body) if paragraph.strip()]
    if not paragraphs:
        paragraphs = [body]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            # Cut long single-line paragraphs at sentence boundaries.
            sentences = re.split(r"(?<=[。！？!?；;])", paragraph)
            piece = ""
            for sentence in sentences:
                if not sentence:
                    continue
                if len(piece) + len(sentence) > max_chars and piece:
                    chunks.append(piece)
                    piece = ""
                piece += sentence
            if piece:
                buffer = piece
            continue
        if buffer and len(buffer) + len(paragraph) + 2 > max_chars:
            chunks.append(buffer)
            buffer = paragraph
        else:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
    if buffer:
        chunks.append(buffer)
    return chunks


class BookStore:
    def __init__(self, data_dir: Path):
        self.books_dir = Path(data_dir) / "books"
        self._lock = threading.RLock()
        self.books_dir.mkdir(parents=True, exist_ok=True)

    # Internals -------------------------------------------------------------

    def _book_dir(self, book_id: str) -> Path:
        return self.books_dir / _safe_id(book_id)

    def _load_book(self, book_id: str) -> dict[str, Any]:
        path = self._book_dir(book_id) / "book.json"
        if not path.is_file():
            raise KeyError(f"书不存在: {book_id}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise KeyError(f"书数据损坏: {book_id}") from exc

    def _save_book(self, book: dict[str, Any]) -> None:
        path = self._book_dir(str(book["book_id"])) / "book.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def _load_index(self, book_id: str) -> list[dict[str, Any]]:
        path = self._book_dir(book_id) / "chapters.json"
        if not path.is_file():
            return []
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            return rows if isinstance(rows, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_index(self, book_id: str, rows: list[dict[str, Any]]) -> None:
        path = self._book_dir(book_id) / "chapters.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def _chapter_path(self, book_id: str, chapter_id: str) -> Path:
        return self._book_dir(book_id) / "chapters" / f"{_safe_id(chapter_id)}.txt"

    def analysis_directory(self, book_id: str) -> Path:
        """Return the book-local analysis workspace after validating the book."""
        with self._lock:
            self._load_book(book_id)
            path = self._book_dir(book_id) / "analysis"
            path.mkdir(parents=True, exist_ok=True)
            return path

    def _branches_path(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "branches.json"

    def _load_branches(self, book_id: str) -> list[dict[str, Any]]:
        self._load_book(book_id)
        path = self._branches_path(book_id)
        if not path.is_file():
            return []
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            return rows if isinstance(rows, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_branches(self, book_id: str, rows: list[dict[str, Any]]) -> None:
        path = self._branches_path(book_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def _recompute_totals(self, book: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        book["chapter_count"] = len(rows)
        book["total_chars"] = sum(int(row.get("char_count") or 0) for row in rows)
        book["updated_at"] = _now()

    @staticmethod
    def _mark_analysis_stale(book: dict[str, Any]) -> None:
        analysis = book.get("analysis")
        if isinstance(analysis, dict):
            analysis["stale"] = True

    # Books ----------------------------------------------------------------

    def list_books(self) -> list[dict[str, Any]]:
        with self._lock:
            rows: list[dict[str, Any]] = []
            for path in sorted(self.books_dir.glob("*/book.json")):
                try:
                    book = json.loads(path.read_text(encoding="utf-8"))
                    rows.append(
                        {
                            "book_id": str(book.get("book_id") or ""),
                            "name": str(book.get("name") or "未命名"),
                            "genre": str(book.get("genre") or "未分类"),
                            "summary": str(book.get("summary") or ""),
                            "source_encoding": str(book.get("source_encoding") or ""),
                            "chapter_count": int(book.get("chapter_count") or 0),
                            "total_chars": int(book.get("total_chars") or 0),
                            "updated_at": str(book.get("updated_at") or ""),
                        }
                    )
                except (OSError, json.JSONDecodeError):
                    continue
            return sorted(rows, key=lambda item: item["updated_at"], reverse=True)

    def import_txt(
        self,
        name: str,
        text: str,
        genre: str = "",
        summary: str = "",
        source_encoding: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            book_id = _new_id("book")
            chapters = split_txt_chapters(text)
            if not chapters:
                raise ValueError("TXT 内容为空，无法导入")
            book_dir = self._book_dir(book_id)
            chapters_dir = book_dir / "chapters"
            chapters_dir.mkdir(parents=True, exist_ok=True)
            rows: list[dict[str, Any]] = []
            summaries: dict[str, str] = {}
            for order, chapter in enumerate(chapters, start=1):
                chapter_id = _new_id("ch")
                content = chapter["content"]
                rows.append(
                    {
                        "id": chapter_id,
                        "title": chapter["title"][:120],
                        "order": order,
                        "char_count": len(content),
                        "created_at": _now(),
                        "updated_at": _now(),
                    }
                )
                self._chapter_path(book_id, chapter_id).write_text(content, encoding="utf-8")
                summaries[chapter_id] = _heuristic_summary(content)
            book = {
                "book_id": book_id,
                "name": name.strip() or "未命名小说",
                "genre": genre.strip() or "未分类",
                "summary": summary.strip() or _heuristic_summary(text[:4000]),
                "source_encoding": source_encoding.strip()[:32],
                "created_at": _now(),
                "updated_at": _now(),
                "chapter_count": len(rows),
                "total_chars": sum(len(c["content"]) for c in chapters),
                "summaries": summaries,
            }
            self._save_book(book)
            self._save_index(book_id, rows)
            return self.get_book(book_id)

    def get_book(self, book_id: str) -> dict[str, Any]:
        with self._lock:
            book = self._load_book(book_id)
            rows = self._load_index(book_id)
            return {
                "book_id": str(book.get("book_id") or ""),
                "name": str(book.get("name") or ""),
                "genre": str(book.get("genre") or ""),
                "summary": str(book.get("summary") or ""),
                "source_encoding": str(book.get("source_encoding") or ""),
                "chapter_count": int(book.get("chapter_count") or 0),
                "total_chars": int(book.get("total_chars") or 0),
                "updated_at": str(book.get("updated_at") or ""),
                "analysis": book.get("analysis"),
                "chapters": [
                    {
                        "id": str(row["id"]),
                        "title": str(row.get("title") or ""),
                        "order": int(row.get("order") or 0),
                        "char_count": int(row.get("char_count") or 0),
                    }
                    for row in rows
                ],
            }

    def delete_book(self, book_id: str) -> None:
        with self._lock:
            import shutil

            target = self._book_dir(book_id)
            if not target.is_dir():
                raise KeyError(f"书籍不存在: {book_id}")
            shutil.rmtree(target)

    # Chapters -------------------------------------------------------------

    def get_chapter(self, book_id: str, chapter_id: str) -> dict[str, Any]:
        with self._lock:
            rows = self._load_index(book_id)
            row = next((item for item in rows if item["id"] == chapter_id), None)
            if row is None:
                raise KeyError(f"章节不存在: {chapter_id}")
            path = self._chapter_path(book_id, chapter_id)
            content = path.read_text(encoding="utf-8") if path.is_file() else ""
            return {
                "id": chapter_id,
                "title": str(row.get("title") or ""),
                "order": int(row.get("order") or 0),
                "content": content,
                "char_count": len(content),
            }

    def save_chapter(self, book_id: str, chapter_id: str, title: str, content: str) -> dict[str, Any]:
        with self._lock:
            book = self._load_book(book_id)
            rows = self._load_index(book_id)
            row = next((item for item in rows if item["id"] == chapter_id), None)
            if row is None:
                raise KeyError(f"章节不存在: {chapter_id}")
            row["title"] = title.strip()[:120] or row.get("title") or "未命名章节"
            row["char_count"] = len(content or "")
            row["updated_at"] = _now()
            self._chapter_path(book_id, chapter_id).write_text(content or "", encoding="utf-8")
            book.setdefault("summaries", {})[chapter_id] = _heuristic_summary(content or "")
            self._mark_analysis_stale(book)
            self._recompute_totals(book, rows)
            self._save_book(book)
            self._save_index(book_id, rows)
            return self.get_chapter(book_id, chapter_id)

    def append_chapter(self, book_id: str, title: str, content: str) -> dict[str, Any]:
        with self._lock:
            book = self._load_book(book_id)
            rows = self._load_index(book_id)
            chapter_id = _new_id("ch")
            rows.append(
                {
                    "id": chapter_id,
                    "title": title.strip()[:120] or f"第{len(rows) + 1}章",
                    "order": len(rows) + 1,
                    "char_count": len(content or ""),
                    "created_at": _now(),
                    "updated_at": _now(),
                }
            )
            self._chapter_path(book_id, chapter_id).write_text(content or "", encoding="utf-8")
            book.setdefault("summaries", {})[chapter_id] = _heuristic_summary(content or "")
            self._mark_analysis_stale(book)
            self._recompute_totals(book, rows)
            self._save_book(book)
            self._save_index(book_id, rows)
            return self.get_book(book_id)

    def merge_chapters(
        self,
        book_id: str,
        start_order: int,
        end_order: int,
        title: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            book = self._load_book(book_id)
            rows = self._load_index(book_id)
            start = max(1, int(start_order))
            end = min(len(rows), int(end_order))
            if start > end or not rows:
                raise ValueError("章节范围无效")
            selected = rows[start - 1 : end]
            parts: list[str] = []
            for row in selected:
                path = self._chapter_path(book_id, row["id"])
                if path.is_file():
                    parts.append(path.read_text(encoding="utf-8"))
                else:
                    parts.append("")
            merged_title = title.strip() or f"第{start}–{end}章合并"
            merged_id = _new_id("ch")
            merged_row = {
                "id": merged_id,
                "title": merged_title[:120],
                "order": start,
                "char_count": sum(len(part) for part in parts),
                "created_at": selected[0].get("created_at") or _now(),
                "updated_at": _now(),
            }
            rest = rows[: start - 1] + rows[end:]
            rest.insert(start - 1, merged_row)
            for index, row in enumerate(rest, start=1):
                row["order"] = index
            self._chapter_path(book_id, merged_id).write_text("\n\n".join(parts), encoding="utf-8")
            for row in selected:
                old_path = self._chapter_path(book_id, row["id"])
                if old_path.is_file():
                    old_path.unlink()
            summaries = book.setdefault("summaries", {})
            for row in selected:
                summaries.pop(row["id"], None)
            summaries[merged_id] = _heuristic_summary("\n\n".join(parts))
            self._mark_analysis_stale(book)
            self._recompute_totals(book, rest)
            self._save_book(book)
            self._save_index(book_id, rest)
            return self.get_book(book_id)

    def restore_book(self, book_id: str, chapters: list[dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            book = self._load_book(book_id)
            chapters_dir = self._book_dir(book_id) / "chapters"
            if chapters_dir.is_dir():
                for old in chapters_dir.glob("*.txt"):
                    old.unlink()
            else:
                chapters_dir.mkdir(parents=True, exist_ok=True)
            rows: list[dict[str, Any]] = []
            summaries: dict[str, str] = {}
            book["summaries"] = summaries
            for item in chapters or []:
                chapter_id = _safe_id(str(item.get("id") or _new_id("ch")))
                content = str(item.get("content") or "")
                order = int(item.get("order") or (len(rows) + 1))
                rows.append(
                    {
                        "id": chapter_id,
                        "title": str(item.get("title") or f"第{order}章")[:120],
                        "order": order,
                        "char_count": len(content),
                        "created_at": str(item.get("created_at") or _now()),
                        "updated_at": _now(),
                    }
                )
                self._chapter_path(book_id, chapter_id).write_text(content, encoding="utf-8")
                summaries[chapter_id] = _heuristic_summary(content)
            rows.sort(key=lambda row: int(row.get("order") or 0))
            self._mark_analysis_stale(book)
            self._recompute_totals(book, rows)
            self._save_book(book)
            self._save_index(book_id, rows)
            return self.get_book(book_id)

    def chapter_summaries(self, book_id: str, before_order: int, limit: int = 3) -> list[dict[str, Any]]:
        with self._lock:
            book = self._load_book(book_id)
            rows = self._load_index(book_id)
            summaries = book.get("summaries") or {}
            selected = [row for row in rows if int(row.get("order") or 0) < before_order]
            return [
                {
                    "order": int(row.get("order") or 0),
                    "title": str(row.get("title") or ""),
                    "summary": str(summaries.get(row["id"]) or _heuristic_summary("")),
                }
                for row in selected[-limit:]
            ]

    # Long-novel understanding ---------------------------------------------

    def book_analysis(self, book_id: str) -> dict[str, Any]:
        """Return the latest stored analysis, or a local index on first use."""
        with self._lock:
            book = self._load_book(book_id)
            analysis = book.get("analysis")
            if isinstance(analysis, dict) and (
                analysis.get("updated_at")
                or any(
                    analysis.get(key)
                    for key in ("characters", "settings", "relations", "key_facts", "unresolved_threads")
                )
            ):
                return analysis
            heuristic = self.heuristic_analysis(book_id)
            book["analysis"] = heuristic
            book["analysis"]["updated_at"] = _now()
            self._save_book(book)
            return heuristic

    def save_analysis(self, book_id: str, analysis: dict[str, Any]) -> dict[str, Any]:
        """Persist a normalized full-book analysis assembled by the analysis engine."""
        if not isinstance(analysis, dict):
            raise ValueError("全书档案格式无效")
        with self._lock:
            book = self._load_book(book_id)
            analysis["stale"] = False
            book["analysis"] = analysis
            self._save_book(book)
            return analysis

    def heuristic_analysis(self, book_id: str) -> dict[str, Any]:
        with self._lock:
            rows = self._load_index(book_id)
            counter: dict[str, int] = {}
            first_seen: dict[str, int] = {}
            for row in rows:
                path = self._chapter_path(book_id, row["id"])
                if not path.is_file():
                    continue
                content = path.read_text(encoding="utf-8", errors="ignore")
                order = int(row.get("order") or 0)
                for match in _NAMED_ACTION.finditer(content):
                    name = match.group(1)
                    if name in _STOPWORDS:
                        continue
                    counter[name] = counter.get(name, 0) + 1
                    first_seen.setdefault(name, order)
                for match in _ENGLISH_NAME.finditer(content):
                    name = match.group(0)
                    counter[name] = counter.get(name, 0) + 1
                    first_seen.setdefault(name, order)
            characters = [
                {
                    "name": name,
                    "aliases": [],
                    "role": "（待补充）",
                    "first_chapter": first_seen.get(name, 0),
                    "last_chapter": first_seen.get(name, 0),
                    "notes": f"离线提取，全书记录出现 {count} 次",
                    "source_chapters": [first_seen.get(name, 0)],
                }
                for name, count in sorted(counter.items(), key=lambda item: item[1], reverse=True)
                if count >= 3
            ][:40]
            return {
                "summary": "",
                "characters": characters,
                "settings": [],
                "relations": [],
                "timeline": [],
                "key_facts": [],
                "unresolved_threads": [],
                "resolved_threads": [],
                "offline": True,
            }

    def build_summary_messages(self, book_id: str, chapter_id: str) -> list[dict[str, str]]:
        chapter = self.get_chapter(book_id, chapter_id)
        book = self._load_book(book_id)
        system = "你是一位小说编辑，负责为长篇作品维护章节摘要。"
        user = (
            f"书名：《{book.get('name') or '未命名'}》\n"
            f"章节：第 {chapter['order']} 章《{chapter['title']}》\n\n"
            f"正文：\n{chapter['content'][:6000]}\n\n"
            "请用 150 字以内概括本章：发生的关键事件、登场或变化的人物、"
            "新增的设定/物品/伏笔。只输出摘要正文，不要解释。"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # Branch writing -------------------------------------------------------

    @staticmethod
    def _resolve_text_offset(content: str, offset: int, anchor: str = "") -> int:
        requested = min(len(content), max(0, int(offset)))
        needle = anchor.strip()
        if not needle:
            return requested

        candidates: list[int] = []
        cursor = 0
        while True:
            found = content.find(needle, cursor)
            if found < 0:
                break
            candidates.append(found + len(needle))
            cursor = found + 1
        if not candidates:
            return requested
        return min(candidates, key=lambda candidate: abs(candidate - requested))

    @staticmethod
    def _branch_lineage(
        rows: list[dict[str, Any]], branch_id: str
    ) -> list[dict[str, Any]]:
        by_id = {str(row.get("branch_id") or ""): row for row in rows}
        current = by_id.get(branch_id)
        if current is None:
            raise KeyError(f"分支不存在: {branch_id}")

        lineage: list[dict[str, Any]] = []
        visited: set[str] = set()
        while current is not None:
            current_id = str(current.get("branch_id") or "")
            if current_id in visited:
                raise ValueError("分支谱系存在循环引用")
            visited.add(current_id)
            lineage.append(current)
            parent_id = str(current.get("parent_branch_id") or "")
            if not parent_id:
                break
            current = by_id.get(parent_id)
            if current is None:
                raise KeyError(f"父分支不存在: {parent_id}")
        lineage.reverse()
        return lineage

    def _materialize_branch_text(
        self,
        book_id: str,
        lineage: list[dict[str, Any]],
        final_offset: int | None = None,
    ) -> str:
        root = lineage[0]
        chapter = self.get_chapter(book_id, str(root.get("chapter_id") or ""))
        original = str(chapter.get("content") or "")
        root_offset = min(len(original), max(0, int(root.get("offset") or 0)))
        parts = [original[:root_offset].rstrip()]
        for index, branch in enumerate(lineage):
            text = str(branch.get("text") or "")
            if index + 1 < len(lineage):
                child_offset = int(lineage[index + 1].get("offset") or 0)
                text = text[: min(len(text), max(0, child_offset))]
            elif final_offset is not None:
                text = text[: min(len(text), max(0, final_offset))]
            if text.strip():
                parts.append(text.strip())
        return "\n\n".join(part for part in parts if part)

    def resolve_branch_offset(
        self,
        book_id: str,
        chapter_id: str,
        offset: int,
        anchor: str = "",
    ) -> int:
        """Resolve a UI reading position to a stable source-text offset."""
        chapter = self.get_chapter(book_id, chapter_id)
        content = str(chapter.get("content") or "")
        return self._resolve_text_offset(content, offset, anchor)

    def build_branch_messages(
        self,
        book_id: str,
        chapter_id: str,
        offset: int,
        guidance: str,
        anchor: str = "",
        tail_chars: int = 3600,
        parent_branch_id: str = "",
    ) -> tuple[list[dict[str, str]], int]:
        chapter = self.get_chapter(book_id, chapter_id)
        if parent_branch_id:
            rows = self._load_branches(book_id)
            lineage = self._branch_lineage(rows, parent_branch_id)
            parent = lineage[-1]
            if str(parent.get("chapter_id") or "") != chapter_id:
                raise ValueError("父分支与当前章节不一致")
            parent_text = str(parent.get("text") or "")
            resolved_offset = self._resolve_text_offset(parent_text, offset, anchor)
            prefix = self._materialize_branch_text(
                book_id, lineage, final_offset=resolved_offset
            )
            prompt_label = f"故事路径第 {len(lineage) + 1} 层分叉"
        else:
            resolved_offset = self.resolve_branch_offset(book_id, chapter_id, offset, anchor)
            prefix = str(chapter.get("content") or "")[:resolved_offset]
            prompt_label = "原作正文分叉"
        messages = self.build_ai_write_messages(
            book_id,
            chapter_id,
            "continue",
            guidance,
            text=None,
            tail_chars=tail_chars,
        )
        messages[-1]["content"] = re.sub(
            r"本章末尾：\n.*\Z",
            (
                f"{prompt_label}，分支锚点位于当前来源第 {resolved_offset} 字。下面是这条故事路径在锚点前的完整上下文：\n"
                f"{prefix[-tail_chars:]}\n\n"
                "请从锚点之后写一条真正改变事件走向的新分支。让人物选择带来明确后果，并留下至少一个可继续分叉的悬念。"
                "不要复述已有句子，不要沿用或总结原书在锚点后的内容；只输出新分支正文，不要标题、解释或方案列表。"
            ),
            messages[-1]["content"],
            flags=re.DOTALL,
        )
        return messages, resolved_offset

    def list_branches(self, book_id: str, chapter_id: str = "") -> list[dict[str, Any]]:
        with self._lock:
            rows = self._load_branches(book_id)
            child_counts: dict[str, int] = {}
            for row in rows:
                parent_id = str(row.get("parent_branch_id") or "")
                if parent_id:
                    child_counts[parent_id] = child_counts.get(parent_id, 0) + 1
            enriched = []
            for row in rows:
                branch_id = str(row.get("branch_id") or "")
                item = dict(row)
                item["children_count"] = child_counts.get(branch_id, 0)
                item["is_leaf"] = item["children_count"] == 0
                enriched.append(item)
            rows = enriched
            if chapter_id:
                rows = [row for row in rows if str(row.get("chapter_id") or "") == chapter_id]
            return sorted(rows, key=lambda row: str(row.get("updated_at") or ""), reverse=True)

    def get_branch_path(self, book_id: str, branch_id: str) -> dict[str, Any]:
        with self._lock:
            rows = self._load_branches(book_id)
            lineage = self._branch_lineage(rows, branch_id)
            selected = lineage[-1]
            chapter = self.get_chapter(book_id, str(selected.get("chapter_id") or ""))
            return {
                "branch": dict(selected),
                "lineage": [dict(row) for row in lineage],
                "chapter": {
                    "id": str(chapter.get("id") or ""),
                    "title": str(chapter.get("title") or ""),
                    "order": int(chapter.get("order") or 0),
                },
                "text": self._materialize_branch_text(book_id, lineage),
            }

    def store_branch(
        self,
        book_id: str,
        chapter_id: str,
        offset: int,
        guidance: str,
        text: str,
        offline: bool = False,
        parent_branch_id: str = "",
        kind: str = "free",
        title: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            rows = self._load_branches(book_id)
            parent = None
            if parent_branch_id:
                parent = next(
                    (row for row in rows if row.get("branch_id") == parent_branch_id),
                    None,
                )
                if parent is None:
                    raise KeyError(f"父分支不存在: {parent_branch_id}")
                if str(parent.get("chapter_id") or "") != chapter_id:
                    raise ValueError("父分支与当前章节不一致")
            chapter = self.get_chapter(book_id, chapter_id)
            content = str(parent.get("text") or "") if parent else str(chapter.get("content") or "")
            resolved_offset = min(len(content), max(0, int(offset)))
            now = _now()
            branch_id = _new_id("branch")
            normalized_kind = kind if kind in {"choice", "relationship", "clue", "free"} else "free"
            clean_guidance = guidance.strip()
            clean_title = re.sub(r"\s+", " ", title.strip() or clean_guidance or "未命名分支")[:28]
            depth = int(parent["depth"]) + 1 if parent else 0
            branch = {
                "branch_id": branch_id,
                "book_id": book_id,
                "chapter_id": chapter_id,
                "chapter_title": str(chapter.get("title") or ""),
                "chapter_order": int(chapter.get("order") or 0),
                "parent_branch_id": parent_branch_id,
                "root_branch_id": str(parent["root_branch_id"]) if parent else branch_id,
                "root_offset": int(parent["root_offset"]) if parent else resolved_offset,
                "depth": depth,
                "offset": resolved_offset,
                "progress": round((resolved_offset / max(1, len(content))) * 100, 2),
                "anchor": content[max(0, resolved_offset - 120) : resolved_offset],
                "title": clean_title,
                "kind": normalized_kind,
                "guidance": clean_guidance,
                "text": text.strip(),
                "offline": bool(offline),
                "created_at": now,
                "updated_at": now,
            }
            rows.append(branch)
            self._save_branches(book_id, rows)
            return branch

    def delete_branch(self, book_id: str, branch_id: str) -> dict[str, Any]:
        with self._lock:
            rows = self._load_branches(book_id)
            if not any(str(row.get("branch_id") or "") == branch_id for row in rows):
                raise KeyError(f"分支不存在: {branch_id}")
            remove_ids = {branch_id}
            changed = True
            while changed:
                before = len(remove_ids)
                remove_ids.update(
                    str(row.get("branch_id") or "")
                    for row in rows
                    if str(row.get("parent_branch_id") or "") in remove_ids
                )
                changed = len(remove_ids) != before
            self._save_branches(
                book_id,
                [row for row in rows if str(row.get("branch_id") or "") not in remove_ids],
            )
            return {"branch_id": branch_id, "deleted_ids": sorted(remove_ids), "count": len(remove_ids)}

    def build_workbench_project(self, book_id: str, branch_id: str = "") -> dict[str, Any]:
        """Materialize an imported book and its analysis as an editable project."""
        with self._lock:
            book = self.get_book(book_id)
            analysis = self.book_analysis(book_id)
            branch = None
            branch_path = None
            if branch_id:
                branch = next(
                    (row for row in self._load_branches(book_id) if row.get("branch_id") == branch_id),
                    None,
                )
                if branch is None:
                    raise KeyError(f"分支不存在: {branch_id}")
                branch_path = self.get_branch_path(book_id, branch_id)

            chapter_rows: list[dict[str, str]] = []
            branch_order = int(branch.get("chapter_order") or 0) if branch else 0
            for row in book.get("chapters") or []:
                order = int(row.get("order") or 0)
                if branch and order > branch_order:
                    break
                chapter = self.get_chapter(book_id, str(row.get("id") or ""))
                content = str(chapter.get("content") or "")
                title = str(chapter.get("title") or f"第{order}章")
                if branch and str(row.get("id") or "") == str(branch.get("chapter_id") or ""):
                    content = str((branch_path or {}).get("text") or "")
                    title = f"{title} · 分支"
                chapter_rows.append(
                    {"id": _new_id("chapter"), "title": title, "content": content}
                )

            relations = [item for item in (analysis.get("relations") or []) if isinstance(item, dict)]
            characters: list[dict[str, Any]] = []
            for item in analysis.get("characters") or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "未命名")
                character_relations = []
                for relation in relations:
                    source = str(relation.get("from") or "")
                    target = str(relation.get("to") or "")
                    if source == name:
                        character_relations.append(
                            {"name": target, "relation": str(relation.get("relation") or "有关联")}
                        )
                    elif target == name:
                        character_relations.append(
                            {"name": source, "relation": str(relation.get("relation") or "有关联")}
                        )
                characters.append(
                    {
                        "id": _new_id("character"),
                        "name": name,
                        "identity": str(item.get("role") or ""),
                        "role": str(item.get("role") or "配角"),
                        "age": "",
                        "stance": "",
                        "drive": "",
                        "fear": "",
                        "traits": "",
                        "abilities": "",
                        "weakness": "",
                        "secret": "",
                        "speech": "",
                        "appearance": "",
                        "background": str(item.get("notes") or ""),
                        "relationships": character_relations,
                        "status": "正常",
                        "notes": f"首次出现：第 {int(item.get('first_chapter') or 0)} 章",
                    }
                )

            def world_type(value: Any) -> str:
                raw = str(value or "").strip()
                if any(token in raw for token in ("势力", "组织", "家族", "阵营")):
                    return "势力"
                if any(token in raw for token in ("物品", "道具", "武器")):
                    return "物品"
                if any(token in raw for token in ("规则", "制度", "能力")):
                    return "规则"
                return "地点"

            world: list[dict[str, Any]] = []
            location_settings: list[dict[str, Any]] = []
            for item in analysis.get("settings") or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "未命名")
                normalized_type = world_type(item.get("type"))
                related = [
                    f"{relation.get('from')} — {relation.get('relation') or '有关联'} — {relation.get('to')}"
                    for relation in relations
                    if name in {str(relation.get("from") or ""), str(relation.get("to") or "")}
                ]
                notes = str(item.get("notes") or "")
                details = "\n".join(part for part in (notes, *related) if part)
                world.append(
                    {
                        "id": _new_id("world"),
                        "name": name,
                        "type": normalized_type,
                        "summary": notes[:160],
                        "details": details,
                        "significance": "由导入小说自动整理",
                        "tags": "导入小说",
                    }
                )
                if normalized_type == "地点":
                    location_settings.append(item)

            map_nodes = []
            map_node_ids: dict[str, str] = {}
            for index, item in enumerate(location_settings):
                node_id = _new_id("map-node")
                name = str(item.get("name") or "未命名")
                map_node_ids[name] = node_id
                map_nodes.append(
                    {
                        "id": node_id,
                        "name": name,
                        "x": 120 + (index % 4) * 240,
                        "y": 120 + (index // 4) * 180,
                        "description": str(item.get("notes") or ""),
                    }
                )
            map_edges = []
            seen_edges: set[tuple[str, str]] = set()
            for relation in relations:
                source = map_node_ids.get(str(relation.get("from") or ""))
                target = map_node_ids.get(str(relation.get("to") or ""))
                if not source or not target or source == target:
                    continue
                key = tuple(sorted((source, target)))
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                map_edges.append({"id": _new_id("map-edge"), "from": source, "to": target})

            suffix = " · 分支" if branch else " · 创作本"
            source_note = f"基于导入小说《{book.get('name') or '未命名'}》建立"
            return {
                "id": _new_id("project"),
                "name": f"{book.get('name') or '未命名'}{suffix}",
                "genre": str(book.get("genre") or "未分类"),
                "summary": str(book.get("summary") or ""),
                "global_guidance": f"{source_note}，续写时保持原作人物、设定与时间线一致。",
                "chapter_turns": 4,
                "writing_style": "",
                "polish_writing": True,
                "style_example": "",
                "style_notes": "",
                "style_avoid": "",
                "source_book_id": book_id,
                "source_branch_id": str(branch.get("branch_id") or "") if branch else "",
                "world": world,
                "characters": characters,
                "map": {"nodes": map_nodes, "edges": map_edges},
                "chapters": chapter_rows,
                "chat": [],
                "issues": [
                    {
                        "id": _new_id("issue"),
                        "kind": "提醒",
                        "item": _analysis_text(thread),
                        "reason": "原作中尚未回收的伏笔或悬念",
                        "suggestion": "续写时决定推进、回收或明确搁置。",
                        "status": "待处理",
                        "created_at": _now(),
                    }
                    for thread in (analysis.get("unresolved_threads") or [])
                    if _analysis_text(thread)
                ],
            }

    def store_chapter_summary(self, book_id: str, chapter_id: str, text: str) -> str:
        summary = text.strip() or _heuristic_summary("")
        with self._lock:
            book = self._load_book(book_id)
            book.setdefault("summaries", {})[chapter_id] = summary
            self._save_book(book)
            return summary

    # AI context -----------------------------------------------------------

    def build_ai_write_messages(
        self,
        book_id: str,
        chapter_id: str,
        mode: str,
        guidance: str,
        text: str | None = None,
        tail_chars: int = 2600,
    ) -> list[dict[str, str]]:
        """Build a bounded prompt for continue/rewrite/expand.

        Long novels are represented as: book summary + previous chapter
        summaries + current chapter tail/selection, never the full text.
        """
        book = self._load_book(book_id)
        chapter = self.get_chapter(book_id, chapter_id)
        previous = self.chapter_summaries(book_id, int(chapter["order"]), limit=5)
        prior_text = "\n".join(
            f"第{int(item['order'])}章《{item['title']}》摘要：{item['summary']}"
            for item in previous
        ) or "（这是全书第一章，没有前文摘要。）"
        analysis = self.book_analysis(book_id)
        character_lines = "\n".join(
            f"- {item['name']}（{item.get('role') or '角色'}，首现第{item.get('first_chapter') or '?'}章）："
            f"{item.get('notes') or ''}"
            for item in (analysis.get("characters") or [])[:24]
        ) or "（暂无角色索引）"
        setting_lines = "\n".join(
            f"- {item['name']}（{item.get('type') or '地点'}）：{item.get('notes') or ''}"
            for item in (analysis.get("settings") or [])[:16]
        ) or "（暂无设定索引）"
        fact_lines = (
            "\n".join(
                f"- {_analysis_text(item)}"
                for item in (analysis.get("key_facts") or [])[:16]
                if _analysis_text(item)
            )
            or "（暂无）"
        )
        thread_lines = (
            "\n".join(
                f"- {_analysis_text(item)}"
                for item in (analysis.get("unresolved_threads") or [])[:16]
                if _analysis_text(item)
            )
            or "（暂无）"
        )

        mode_name = {"continue": "续写", "rewrite": "改写", "expand": "扩写"}.get(mode, "续写")
        guidance_line = f"用户引导：{guidance.strip()}" if guidance.strip() else "用户引导：无，按故事自然走向。"

        if mode == "rewrite" or mode == "expand":
            target = (text or "").strip() or chapter["content"]
            if mode == "rewrite":
                instruction = (
                    "请改写以下正文：保留全部情节、人物和关键信息，提升文笔、节奏与画面感，"
                    "去掉AI腔和套话，输出改写后的完整正文，不要解释。"
                )
            else:
                instruction = (
                    "请扩写以下正文：不改变情节走向，补充环境、动作、心理、对白与细节，"
                    "让段落更丰满，输出扩写后的完整正文，不要解释。"
                )
            content_block = f"目标正文：\n{target[:12000]}"
        else:
            instruction = (
                "请紧接以下文本续写下一段：延续人物语气、叙事风格和时间线，"
                "不跳时间、不写大结局，输出续写的正文，不要解释。"
            )
            content_block = f"本章末尾：\n{chapter['content'][-tail_chars:]}"

        system = (
            "你是一位资深中文小说作者与编辑。写作要求："
            "1) 严格忠于前文设定、人物性格、说话方式和时间线；"
            "2) 长短句交替，控制节奏，段落留白；"
            "3) 避免AI腔（慎用“仿佛、不禁、然而、不禁让人”等套话）；"
            "4) 不发明与已知信息冲突的情节，不改变已确认事实；"
            "5) 尊重角色索引与待回收伏笔，续写时可以推进伏笔但不能凭空推翻设定；"
            "6) 与全书文风保持一致。"
        )
        user = (
            f"书名：《{book.get('name') or '未命名'}》\n"
            f"类型：{book.get('genre') or '未分类'}\n"
            f"全书简介：{book.get('summary') or '无'}\n\n"
            f"角色索引：\n{character_lines}\n\n"
            f"设定索引：\n{setting_lines}\n\n"
            f"已确认事实：\n{fact_lines}\n\n"
            f"待回收伏笔：\n{thread_lines}\n\n"
            f"前文摘要：\n{prior_text}\n\n"
            f"{guidance_line}\n\n"
            f"{instruction}\n\n"
            f"{content_block}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


def _heuristic_summary(content: str, limit: int = 200) -> str:
    text = (content or "").strip().replace("\n", " ")
    if not text:
        return "（无内容）"
    return text[:limit] + ("……" if len(text) > limit else "")


def _analysis_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or value.get("summary") or "").strip()
    return str(value or "").strip()

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
    r"|(?:卷一|卷首|序章|楔子|引子|序幕|前言|尾声|后记|番外|终章|大结局).*"
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
        if content:
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

    def _recompute_totals(self, book: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        book["chapter_count"] = len(rows)
        book["total_chars"] = sum(int(row.get("char_count") or 0) for row in rows)
        book["updated_at"] = _now()

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
                            "chapter_count": int(book.get("chapter_count") or 0),
                            "total_chars": int(book.get("total_chars") or 0),
                            "updated_at": str(book.get("updated_at") or ""),
                        }
                    )
                except (OSError, json.JSONDecodeError):
                    continue
            return sorted(rows, key=lambda item: item["updated_at"], reverse=True)

    def import_txt(self, name: str, text: str, genre: str = "", summary: str = "") -> dict[str, Any]:
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
            if target.is_dir():
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
            book.setdefault("summaries", {})[merged_id] = _heuristic_summary("\n\n".join(parts))
            self._recompute_totals(book, rest)
            self._save_book(book)
            self._save_index(book_id, rest)
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
        """Return the stored analysis, or build a heuristic one on first use."""
        with self._lock:
            book = self._load_book(book_id)
            analysis = book.get("analysis")
            if isinstance(analysis, dict) and analysis.get("characters"):
                return analysis
            heuristic = self.heuristic_analysis(book_id)
            book["analysis"] = heuristic
            book["analysis"]["updated_at"] = _now()
            self._save_book(book)
            return heuristic

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
                    "notes": f"离线提取，全书记录出现 {count} 次",
                }
                for name, count in sorted(counter.items(), key=lambda item: item[1], reverse=True)
                if count >= 3
            ][:40]
            return {
                "characters": characters,
                "settings": [],
                "key_facts": [],
                "unresolved_threads": [],
                "offline": True,
            }

    def build_analyze_messages(self, book_id: str) -> list[dict[str, str]]:
        book = self._load_book(book_id)
        rows = self._load_index(book_id)
        summaries = book.get("summaries") or {}
        summary_lines = [
            f"第{row['order']}章《{row['title']}》：{summaries.get(row['id']) or '（无摘要）'}"
            for row in rows[:60]
        ]
        system = "你是一位资深小说编辑，负责为长篇作品建立稳定的创作档案。"
        user = (
            f"书名：《{book.get('name') or '未命名'}》\n"
            f"类型：{book.get('genre') or '未分类'}\n"
            f"简介：{book.get('summary') or '无'}\n\n"
            f"章节摘要（共 {len(rows)} 章，列出前 60 章）：\n"
            + "\n".join(summary_lines)
            + "\n\n请输出 JSON（不要代码块标记）：\n"
            '{"characters":[{"name":"角色名","aliases":["别名"],"role":"主角/配角/反派/重要角色","first_chapter":1,"notes":"身份与当前状态"}],'
            '"settings":[{"name":"地点/组织/关键物品","type":"地点/组织/物品","notes":"说明"}],'
            '"key_facts":["已确认的设定与事实"],'
            '"unresolved_threads":["尚未回收的伏笔或悬念"]}'
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def store_analysis(self, book_id: str, text: str) -> dict[str, Any]:
        raw = _extract_json_object(text)
        analysis: dict[str, Any] = {
            "characters": [],
            "settings": [],
            "key_facts": [],
            "unresolved_threads": [],
            "offline": False,
            "updated_at": _now(),
        }
        if isinstance(raw, dict):
            analysis["characters"] = [
                {
                    "name": str(item.get("name") or "").strip() or "未命名",
                    "aliases": [str(alias).strip() for alias in (item.get("aliases") or []) if str(alias).strip()],
                    "role": str(item.get("role") or "角色").strip(),
                    "first_chapter": int(item.get("first_chapter") or 0),
                    "notes": str(item.get("notes") or "").strip(),
                }
                for item in (raw.get("characters") or [])
                if isinstance(item, dict)
            ]
            analysis["settings"] = [
                {
                    "name": str(item.get("name") or "").strip() or "未命名",
                    "type": str(item.get("type") or "地点").strip(),
                    "notes": str(item.get("notes") or "").strip(),
                }
                for item in (raw.get("settings") or [])
                if isinstance(item, dict)
            ]
            analysis["key_facts"] = [str(item).strip() for item in (raw.get("key_facts") or []) if str(item).strip()]
            analysis["unresolved_threads"] = [
                str(item).strip() for item in (raw.get("unresolved_threads") or []) if str(item).strip()
            ]
        with self._lock:
            book = self._load_book(book_id)
            book["analysis"] = analysis
            self._save_book(book)
            return analysis

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
        fact_lines = "\n".join(f"- {item}" for item in (analysis.get("key_facts") or [])[:16]) or "（暂无）"
        thread_lines = (
            "\n".join(f"- {item}" for item in (analysis.get("unresolved_threads") or [])[:16]) or "（暂无）"
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


def _extract_json_object(text: str) -> dict[str, Any] | None:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError):
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except (ValueError, TypeError):
            return None
    return None

from __future__ import annotations

import json
import re
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rhine_lore.long_novel_analysis import AnalysisTaskManager, LongNovelAnalyzer
from rhine_lore.novel_store import BookStore


class LongNovelAnalysisTests(unittest.TestCase):
    @staticmethod
    def _fake_chat(calls: list[str]):
        def chat(messages: list[dict[str, str]]) -> str:
            prompt = messages[-1]["content"]
            calls.append(prompt)
            chapter_match = re.search(r"章节：第 (\d+) 项", prompt)
            if chapter_match:
                chapter = int(chapter_match.group(1))
                finding = "发现潮汐表被改写" if "潮汐表被改写" in prompt else "调查继续"
                return json.dumps(
                    {
                        "summary": f"第{chapter}章{finding}。",
                        "characters": [
                            {
                                "name": "林夏",
                                "aliases": [],
                                "role": "主角",
                                "notes": f"在第{chapter}章{finding}",
                                "first_chapter": 1,
                                "last_chapter": chapter,
                                "source_chapters": [chapter],
                            }
                        ],
                        "settings": [],
                        "relations": [],
                        "timeline": [
                            {
                                "title": f"事件{chapter}",
                                "summary": "调查推进",
                                "participants": ["林夏"],
                                "source_chapters": [chapter],
                            }
                        ],
                        "key_facts": [],
                        "unresolved_threads": [],
                        "resolved_threads": [],
                    },
                    ensure_ascii=False,
                )
            sources = sorted({int(value) for value in re.findall(r'"source_chapters": \[(\d+)', prompt)})
            merge_finding = "潮汐表线索进入主线" if "潮汐表" in prompt else "调查持续推进"
            return json.dumps(
                {
                    "summary": f"这一阶段{merge_finding}。",
                    "characters": [
                        {
                            "name": "林夏",
                            "aliases": [],
                            "role": "主角",
                            "notes": "持续调查",
                            "first_chapter": min(sources, default=1),
                            "last_chapter": max(sources, default=1),
                            "source_chapters": sources,
                        }
                    ],
                    "settings": [],
                    "relations": [],
                    "timeline": [],
                    "key_facts": [],
                    "unresolved_threads": [],
                    "resolved_threads": [],
                },
                ensure_ascii=False,
            )

        return chat

    def test_plans_every_chapter_in_a_million_character_book(self) -> None:
        with TemporaryDirectory() as directory:
            store = BookStore(Path(directory))
            chapter_body = "雾沿着码头向前移动。" * 420
            source = "\n\n".join(
                f"第{index}章 潮声{index}\n{chapter_body}" for index in range(1, 251)
            )
            book = store.import_txt("百万字测试", source)

            plan = LongNovelAnalyzer(store).plan(book["book_id"], "smart")

            self.assertEqual(plan["chapter_count"], 250)
            self.assertGreaterEqual(plan["total_chars"], 1_000_000)
            self.assertEqual(
                {unit["chapter_order"] for unit in plan["units"]},
                set(range(1, 251)),
            )
            self.assertTrue(all(len(unit["content"]) <= 9_000 for unit in plan["units"]))
            self.assertGreater(plan["estimated_requests"], plan["fragment_count"])

    def test_reuses_all_cached_nodes_and_only_rebuilds_one_changed_path(self) -> None:
        with TemporaryDirectory() as directory:
            store = BookStore(Path(directory))
            source = "\n\n".join(
                f"第{index}章 雾港{index}\n林夏走过第{index}号码头。"
                for index in range(1, 9)
            )
            book = store.import_txt("雾港来信", source)
            analyzer = LongNovelAnalyzer(store)

            first_calls: list[str] = []
            first = analyzer.run(book["book_id"], self._fake_chat(first_calls), mode="smart")
            self.assertEqual(len(first_calls), analyzer.plan(book["book_id"], "smart")["estimated_requests"])
            self.assertEqual(first["coverage"]["chapters_analyzed"], 8)
            self.assertEqual(len(first["timeline"]), 8)
            self.assertEqual(first["characters"][0]["source_chapters"], list(range(1, 9)))

            cached_calls: list[str] = []
            cached = analyzer.run(book["book_id"], self._fake_chat(cached_calls), mode="smart")
            self.assertEqual(cached_calls, [])
            self.assertEqual(cached["analysis_meta"]["model_requests"], 0)

            third = store.get_book(book["book_id"])["chapters"][2]
            store.save_chapter(book["book_id"], third["id"], third["title"], "林夏发现潮汐表被改写。")
            changed_calls: list[str] = []
            refreshed = analyzer.run(book["book_id"], self._fake_chat(changed_calls), mode="smart")

            self.assertEqual(len(changed_calls), 3)
            self.assertFalse(refreshed["stale"])
            self.assertEqual(refreshed["coverage"]["percent"], 100)

    def test_background_job_can_pause_and_resume_from_persisted_nodes(self) -> None:
        with TemporaryDirectory() as directory:
            store = BookStore(Path(directory))
            source = "\n\n".join(
                f"第{index}章 夜航{index}\n林夏在夜航日志中写下第{index}条记录。"
                for index in range(1, 13)
            )
            book = store.import_txt("夜航日志", source)
            manager = AnalysisTaskManager()
            calls: list[str] = []
            base_chat = self._fake_chat(calls)

            def slow_chat(messages: list[dict[str, str]]) -> str:
                time.sleep(0.025)
                return base_chat(messages)

            manager.start(
                store,
                book["book_id"],
                mode="smart",
                force=False,
                chat=slow_chat,
            )
            for _ in range(100):
                status = manager.status(store, book["book_id"])
                if int(status.get("processed_fragments") or 0) >= 2:
                    break
                time.sleep(0.01)
            manager.cancel(store, book["book_id"])
            self.assertTrue(manager.wait(book["book_id"], timeout=3))
            paused = manager.status(store, book["book_id"])
            self.assertEqual(paused["state"], "cancelled")
            self.assertTrue(paused["can_resume"])
            completed_before_pause = len(calls)

            resumed_calls: list[str] = []
            manager.start(
                store,
                book["book_id"],
                mode="smart",
                force=False,
                chat=self._fake_chat(resumed_calls),
            )
            self.assertTrue(manager.wait(book["book_id"], timeout=5))
            completed = manager.status(store, book["book_id"])
            self.assertEqual(completed["state"], "completed")
            self.assertGreater(completed_before_pause, 0)
            self.assertLess(
                len(resumed_calls),
                LongNovelAnalyzer(store).plan(book["book_id"], "smart")["estimated_requests"],
            )


if __name__ == "__main__":
    unittest.main()

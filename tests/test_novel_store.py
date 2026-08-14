from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rhine_lore.novel_store import BookStore, split_txt_chapters


class NovelStoreTextSplitTests(unittest.TestCase):
    def test_preserves_volume_heading_as_its_own_empty_section(self) -> None:
        chapters = split_txt_chapters(
            "第一卷 潮汐之前\n第一章 雾信\n雾还没有散。\n\n第二章 归港\n潮声盖过了脚步。"
        )

        self.assertEqual([chapter["title"] for chapter in chapters], ["第一卷 潮汐之前", "第一章 雾信", "第二章 归港"])
        self.assertEqual(chapters[0]["content"], "")
        self.assertEqual(chapters[1]["content"], "雾还没有散。")
        self.assertEqual(chapters[2]["content"], "潮声盖过了脚步。")

    def test_preserves_a_trailing_heading_without_body(self) -> None:
        chapters = split_txt_chapters("序章\n风从海上来。\n\n卷二 深水")

        self.assertEqual(chapters[-1], {"title": "卷二 深水", "content": ""})


class NovelStoreBranchTests(unittest.TestCase):
    def test_branch_keeps_original_book_and_materializes_workbench_data(self) -> None:
        with TemporaryDirectory() as directory:
            store = BookStore(Path(directory))
            book = store.import_txt(
                "雾港来信",
                "第一章 雾信\n林夏走进旧港。钟声响起。\n\n第二章 归潮\n她在灯塔下见到了周明。",
                genre="悬疑",
            )
            first = store.get_chapter(book["book_id"], book["chapters"][0]["id"])
            original = first["content"]
            offset = original.index("。") + 1
            branch = store.store_branch(
                book["book_id"],
                first["id"],
                offset,
                "让码头停电",
                "所有灯在同一刻熄灭。",
            )
            messages, resolved_offset = store.build_branch_messages(
                book["book_id"],
                first["id"],
                offset,
                "让码头停电",
            )
            self.assertEqual(resolved_offset, offset)
            branch_prompt = messages[-1]["content"].split("分支锚点", 1)[1]
            self.assertIn("林夏走进旧港。", branch_prompt)
            self.assertNotIn("钟声响起。", branch_prompt)
            store.save_analysis(
                book["book_id"],
                {
                  "characters": [
                    {"name": "林夏", "role": "主角", "first_chapter": 1, "notes": "调查员"},
                    {"name": "周明", "role": "盟友", "first_chapter": 2, "notes": "守塔人"}
                  ],
                  "settings": [
                    {"name": "旧港", "type": "地点", "notes": "临海港区"},
                    {"name": "灯塔", "type": "地点", "notes": "位于旧港北侧"},
                    {"name": "潮汐会", "type": "势力", "notes": "控制航线"}
                  ],
                  "relations": [
                    {"from": "林夏", "to": "周明", "relation": "盟友", "kind": "人物"},
                    {"from": "旧港", "to": "灯塔", "relation": "北侧相连", "kind": "地点"},
                    {"from": "潮汐会", "to": "旧港", "relation": "控制", "kind": "势力"}
                  ],
                  "key_facts": [],
                  "unresolved_threads": [{"text": "失踪船只的去向", "source_chapters": [2]}]
                },
            )

            project = store.build_workbench_project(book["book_id"], branch["branch_id"])
            full_project = store.build_workbench_project(book["book_id"])

            self.assertEqual(store.get_chapter(book["book_id"], first["id"])["content"], original)
            self.assertEqual(len(project["chapters"]), 1)
            self.assertEqual(len(full_project["chapters"]), 2)
            self.assertIn("所有灯在同一刻熄灭。", project["chapters"][0]["content"])
            self.assertEqual({item["name"] for item in project["characters"]}, {"林夏", "周明"})
            self.assertIn(
                {"name": "周明", "relation": "盟友"},
                project["characters"][0]["relationships"],
            )
            self.assertEqual({item["name"] for item in project["world"]}, {"旧港", "灯塔", "潮汐会"})
            self.assertEqual(len(project["map"]["nodes"]), 2)
            self.assertEqual(len(project["map"]["edges"]), 1)
            self.assertEqual(project["source_branch_id"], branch["branch_id"])

    def test_nested_branches_materialize_a_single_story_line(self) -> None:
        with TemporaryDirectory() as directory:
            store = BookStore(Path(directory))
            book = store.import_txt(
                "岔路",
                "第一章 门\n阿岚推开门。门后是长廊。",
            )
            chapter_id = book["chapters"][0]["id"]
            original = store.get_chapter(book["book_id"], chapter_id)["content"]
            root_offset = original.index("。") + 1
            root = store.store_branch(
                book["book_id"],
                chapter_id,
                root_offset,
                "进入地下室",
                "她没有走长廊，而是掀开地毯。暗门下传来钟声。",
                kind="choice",
            )
            child_offset = root["text"].index("。") + 1
            child = store.store_branch(
                book["book_id"],
                chapter_id,
                child_offset,
                "回应钟声",
                "她敲了三下，黑暗里也响起三次回应。",
                parent_branch_id=root["branch_id"],
                kind="clue",
            )
            sibling = store.store_branch(
                book["book_id"],
                chapter_id,
                child_offset,
                "无视钟声",
                "她屏住呼吸，沿石阶继续向下。",
                parent_branch_id=root["branch_id"],
            )

            path = store.get_branch_path(book["book_id"], child["branch_id"])
            self.assertEqual(
                [item["branch_id"] for item in path["lineage"]],
                [root["branch_id"], child["branch_id"]],
            )
            self.assertIn("阿岚推开门。", path["text"])
            self.assertIn("她没有走长廊，而是掀开地毯。", path["text"])
            self.assertIn("她敲了三下", path["text"])
            self.assertNotIn("门后是长廊。", path["text"])
            self.assertNotIn("暗门下传来钟声。", path["text"])
            self.assertNotIn("沿石阶继续向下", path["text"])

            messages, resolved_offset = store.build_branch_messages(
                book["book_id"],
                chapter_id,
                len(child["text"]),
                "让回应者现身",
                parent_branch_id=child["branch_id"],
            )
            self.assertEqual(resolved_offset, len(child["text"]))
            self.assertIn("故事路径第 3 层分叉", messages[-1]["content"])
            self.assertIn("她敲了三下", messages[-1]["content"])
            self.assertNotIn("沿石阶继续向下", messages[-1]["content"])

            project = store.build_workbench_project(book["book_id"], child["branch_id"])
            self.assertEqual(project["chapters"][0]["content"], path["text"])
            branches = store.list_branches(book["book_id"], chapter_id)
            root_row = next(item for item in branches if item["branch_id"] == root["branch_id"])
            self.assertEqual(root_row["children_count"], 2)
            self.assertFalse(root_row["is_leaf"])

            deleted = store.delete_branch(book["book_id"], root["branch_id"])
            self.assertEqual(deleted["count"], 3)
            self.assertEqual(store.list_branches(book["book_id"]), [])


if __name__ == "__main__":
    unittest.main()

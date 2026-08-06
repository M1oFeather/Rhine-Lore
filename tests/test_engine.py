from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rhine_lore.engine import (  # noqa: E402
    EvolutionSettings,
    EvolutionEvent,
    EvolutionState,
    EvolutionStore,
    advance,
    render_novel,
    render_sandbox,
    start_run,
)


CHARACTERS = [
    {"id": "hero", "title": "林澈", "content": "想要查明父亲失踪的真相"},
    {"id": "rival", "title": "沈砚", "content": "目标是继承家族商会，害怕失去地位"},
    {"id": "friend", "title": "小满", "content": "希望和所有人保持朋友关系"},
]

WORLD = [
    {"id": "w1", "title": "雾港", "content": "常年被海雾笼罩的港口城市"},
    {"id": "w2", "title": "沈家商会", "content": "控制着雾港一半的贸易"},
]


class DeterminismTests(unittest.TestCase):
    def test_same_seed_same_story(self) -> None:
        first = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=42)
        second = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=42)
        for _ in range(12):
            first, _ = advance(first, choice_id="fate")
            second, _ = advance(second, choice_id="fate")
        self.assertEqual(render_sandbox(first), render_sandbox(second))

    def test_advance_does_not_mutate_input(self) -> None:
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=7)
        before = render_sandbox(state)
        _, result = advance(state)
        self.assertEqual(render_sandbox(state), before)
        self.assertTrue(result.advanced or result.awaiting_branch)


class BranchTests(unittest.TestCase):
    def test_branch_waits_then_resolves(self) -> None:
        settings = EvolutionSettings(chaos=50, branch_frequency=100, auto_resolve=False)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=3, settings=settings)
        state, result = advance(state)
        self.assertTrue(result.awaiting_branch)
        self.assertIsNotNone(result.branch)
        self.assertIsNotNone(state.pending_branch)
        first_option_id = result.branch.options[0].id

        state, result = advance(state, choice_id=first_option_id)
        self.assertTrue(result.advanced)
        self.assertFalse(result.awaiting_branch)
        self.assertIsNone(state.pending_branch)
        self.assertEqual(len(state.history), 1)
        self.assertEqual(state.history[0].chosen_option_id, first_option_id)

    def test_fate_resolves_branch(self) -> None:
        settings = EvolutionSettings(chaos=50, branch_frequency=100, auto_resolve=False)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=3, settings=settings)
        state, result = advance(state)
        self.assertTrue(result.awaiting_branch)
        state, result = advance(state, choice_id="fate")
        self.assertTrue(result.advanced)
        self.assertIsNotNone(state.history[0].chosen_option_label)

    def test_auto_resolve_setting_never_blocks(self) -> None:
        settings = EvolutionSettings(chaos=50, branch_frequency=100, auto_resolve=True)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=3, settings=settings)
        for _ in range(5):
            state, result = advance(state)
            self.assertTrue(result.advanced)
            self.assertIsNone(state.pending_branch)


class LimitedPerspectiveTests(unittest.TestCase):
    def test_novel_only_contains_visible_events(self) -> None:
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=11)
        state.history = [
            EvolutionEvent(
                id="e1",
                turn=1,
                kind="发现",
                title="只有主角知道的发现",
                summary="林澈在雾港发现了一封没有署名的信。",
                participants=["hero"],
                witnesses=["hero"],
            ),
            EvolutionEvent(
                id="e2",
                turn=2,
                kind="秘密",
                title="沈砚独自经历的秘密",
                summary="沈砚独自查到了商会账簿里的缺口。",
                participants=["rival"],
                witnesses=["rival"],
            ),
            EvolutionEvent(
                id="e3",
                turn=3,
                kind="相遇",
                title="被小满看见的相遇",
                summary="小满远远看见林澈和陌生人交谈。",
                participants=["hero"],
                witnesses=["hero", "friend"],
            ),
        ]
        novel = render_novel(state, "hero")
        self.assertEqual(novel["viewpoint_id"], "hero")
        self.assertEqual(novel["hidden_events"], 1)
        text = "\n".join(paragraph for chapter in novel["chapters"] for paragraph in chapter["paragraphs"])
        self.assertIn("林澈在雾港发现了一封没有署名的信。", text)
        self.assertIn("小满远远看见林澈和陌生人交谈。", text)
        self.assertNotIn("沈砚独自查到了商会账簿里的缺口。", text)

    def test_novel_has_viewpoint_name_and_chapters(self) -> None:
        settings = EvolutionSettings(branch_frequency=0)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=5, settings=settings)
        state, _ = advance(state)
        novel = render_novel(state)
        self.assertEqual(novel["viewpoint_name"], "林澈")
        self.assertGreater(len(novel["chapters"]), 0)


class StoreTests(unittest.TestCase):
    def test_save_load_roundtrip(self) -> None:
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=9)
        for _ in range(4):
            state, _ = advance(state, choice_id="fate")
        with tempfile.TemporaryDirectory() as raw_dir:
            store = EvolutionStore(Path(raw_dir))
            store.save(state)
            loaded = store.load("p1")
            self.assertIsNotNone(loaded)
            self.assertEqual(render_sandbox(loaded), render_sandbox(state))
            self.assertEqual(loaded.cast[0].name, "林澈")
            self.assertEqual(len(loaded.history), len(state.history))

    def test_load_missing_returns_none_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            store = EvolutionStore(Path(raw_dir))
            self.assertIsNone(store.load("nope"))
            state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=9)
            store.save(state)
            self.assertTrue(store.delete("p1"))
            self.assertFalse(store.delete("p1"))
            self.assertIsNone(store.load("p1"))

    def test_sanitizes_project_id(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            store = EvolutionStore(Path(raw_dir))
            state = start_run("我的故事: 1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=9)
            store.save(state)
            loaded = store.load("我的故事: 1")
            self.assertIsNotNone(loaded)


class EndingTests(unittest.TestCase):
    def test_ending_fires_without_active_major_threads(self) -> None:
        settings = EvolutionSettings(branch_frequency=0)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=9, settings=settings)
        state.turn = 19
        state.threads = []
        state, result = advance(state)
        self.assertTrue(result.advanced)
        self.assertTrue(state.ending)
        self.assertEqual(result.ending, state.ending)


if __name__ == "__main__":
    unittest.main()

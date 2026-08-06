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
    build_ai_prose_prompt,
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

    def test_ai_prose_roundtrip(self) -> None:
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, seed=9)
        state.ai_prose["1:hero"] = "林澈沿着河岸往前走。"
        with tempfile.TemporaryDirectory() as raw_dir:
            store = EvolutionStore(Path(raw_dir))
            store.save(state)
            loaded = store.load("p1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.ai_prose, {"1:hero": "林澈沿着河岸往前走。"})

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


class CharacterCardMappingTests(unittest.TestCase):
    def test_rich_character_cards_map_to_cast(self) -> None:
        characters = [
            {
                "id": "hero",
                "name": "林澈",
                "identity": "雾港送信人",
                "role": "主角",
                "drive": "查明父亲失踪的真相",
                "fear": "忘记父亲的模样",
                "traits": "谨慎、固执",
                "background": "在雾港长大",
                "status": "正常",
                "relationships": [
                    {"name": "沈砚", "relation": "死敌"},
                    {"name": "小满", "relation": "挚友"},
                ],
            },
            {"id": "rival", "name": "沈砚", "role": "反派", "status": "死亡"},
            {"id": "friend", "name": "小满", "role": "配角"},
        ]
        state = start_run("p1", "雾港来信", "悬疑", characters, [], seed=1)
        hero, rival, friend = state.cast
        self.assertEqual(hero.identity, "雾港送信人")
        self.assertEqual(hero.drive, "查明父亲失踪的真相")
        self.assertEqual(hero.fear, "忘记父亲的模样")
        self.assertIn("谨慎", hero.traits)
        self.assertIn("固执", hero.traits)
        self.assertEqual(hero.background, "在雾港长大")
        self.assertEqual(hero.relations.get(rival.id), -2)
        self.assertEqual(hero.relations.get(friend.id), 2)
        self.assertFalse(rival.alive)
        self.assertEqual(rival.role, "反派")
        self.assertEqual(friend.role, "配角")

    def test_rich_fields_survive_store_roundtrip(self) -> None:
        characters = [
            {
                "id": "hero",
                "name": "林澈",
                "identity": "雾港送信人",
                "traits": ["谨慎"],
                "background": "雾港长大",
                "secret": "那封信是自己寄出的",
                "abilities": ["认路"],
                "weakness": "怕水",
            },
        ]
        state = start_run("p1", "雾港来信", "悬疑", characters, [], seed=1)
        with tempfile.TemporaryDirectory() as raw_dir:
            store = EvolutionStore(Path(raw_dir))
            store.save(state)
            loaded = store.load("p1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.cast[0].identity, "雾港送信人")
        self.assertEqual(loaded.cast[0].traits, ["谨慎"])
        self.assertEqual(loaded.cast[0].background, "雾港长大")
        self.assertEqual(loaded.cast[0].secret, "那封信是自己寄出的")
        self.assertEqual(loaded.cast[0].abilities, ["认路"])
        self.assertEqual(loaded.cast[0].weakness, "怕水")

    def test_legacy_title_content_characters_still_work(self) -> None:
        characters = [{"id": "a", "title": "林澈", "content": "想要查明真相"}]
        state = start_run("p1", "雾港来信", "悬疑", characters, [], seed=1)
        self.assertEqual(state.cast[0].name, "林澈")
        self.assertEqual(state.cast[0].drive, "想要查明真相")
        self.assertEqual(state.cast[0].identity, "")


class WorldMapTests(unittest.TestCase):
    def test_world_cards_map_by_type(self) -> None:
        world = [
            {"id": "w1", "name": "雾港", "type": "地点", "summary": "海雾笼罩的港口"},
            {"id": "w2", "name": "沈家商会", "type": "势力"},
            {"id": "w3", "name": "雾夜禁行", "type": "规则", "summary": "入夜后不得出港"},
        ]
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, world, seed=1)
        self.assertIn("雾港", state.world.locations)
        self.assertNotIn("雾夜禁行", state.world.locations)
        self.assertEqual(state.world.factions[0].name, "沈家商会")
        self.assertTrue(any("雾夜禁行" in fact for fact in state.world.facts))

    def test_map_nodes_become_locations_and_assign_cast(self) -> None:
        nodes = [
            {"id": "n1", "name": "雾港"},
            {"id": "n2", "name": "旧码头"},
            {"id": "n3", "name": "灯塔"},
        ]
        edges = [
            {"id": "e1", "from": "n1", "to": "n2"},
            {"id": "e2", "from": "n2", "to": "n3"},
        ]
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, [], map_nodes=nodes, map_edges=edges, seed=1)
        self.assertEqual(state.world.locations, ["雾港", "旧码头", "灯塔"])
        self.assertEqual(state.world.connections, [["雾港", "旧码头"], ["旧码头", "灯塔"]])
        self.assertEqual(state.cast[0].location, "雾港")
        self.assertIn(state.cast[1].location, {"旧码头", "灯塔"})

    def test_secret_seeds_foreshadow_thread(self) -> None:
        characters = [{"id": "hero", "name": "林澈", "secret": "那封信其实是自己寄出的"}]
        state = start_run("p1", "雾港来信", "悬疑", characters, [], seed=1)
        secrets = [thread for thread in state.threads if thread.kind == "伏笔" and thread.title == "林澈的秘密"]
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0].secret, "那封信其实是自己寄出的")

    def test_events_move_participants_along_connections(self) -> None:
        settings = EvolutionSettings(branch_frequency=0, chaos=0)
        nodes = [{"id": "n1", "name": "雾港"}, {"id": "n2", "name": "旧码头"}]
        edges = [{"id": "e1", "from": "n1", "to": "n2"}]
        state = start_run(
            "p1",
            "雾港来信",
            "悬疑",
            CHARACTERS,
            [],
            map_nodes=nodes,
            map_edges=edges,
            settings=settings,
            seed=3,
        )
        state, _ = advance(state)
        event = state.history[0]
        for participant_id in event.participants:
            member = next(item for item in state.cast if item.id == participant_id)
            self.assertEqual(member.location, event.location)
            self.assertIn(member.location, {"雾港", "旧码头"})

    def test_ai_prose_prompt_contains_viewpoint_and_events(self) -> None:
        settings = EvolutionSettings(branch_frequency=0)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, settings=settings, seed=5)
        state, _ = advance(state)
        messages = build_ai_prose_prompt(state, "hero")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("雾港来信", messages[1]["content"])
        self.assertIn("林澈", messages[1]["content"])
        self.assertIn("第1回合", messages[1]["content"])

    def test_guidance_biases_events_and_participants(self) -> None:
        settings = EvolutionSettings(branch_frequency=0, chaos=100)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, settings=settings, seed=5)
        state.guidance = "让沈砚背叛林澈"
        state, _ = advance(state)
        event = state.history[0]
        self.assertEqual(event.kind, "背叛")
        self.assertIn("rival", event.participants)
        self.assertIn("hero", event.participants)

    def test_ai_prompt_includes_guidance_and_previous_prose(self) -> None:
        settings = EvolutionSettings(branch_frequency=0)
        state = start_run("p1", "雾港来信", "悬疑", CHARACTERS, WORLD, settings=settings, seed=5)
        state, _ = advance(state)
        state.guidance = "让林澈发现旧码头有火光"
        state.ai_prose["1:hero"] = "林澈沿着河岸慢慢往前走。"
        messages = build_ai_prose_prompt(state, "hero")
        content = messages[1]["content"]
        self.assertIn("导演指令", content)
        self.assertIn("旧码头有火光", content)
        self.assertIn("林澈沿着河岸慢慢往前走", content)


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

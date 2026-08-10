"""Deterministic story evolution engine for Rhine-Lore.

The engine advances a story project turn by turn. Every run has a seed, so
the same seed plus the same choices always produces the same story. The
engine is pure Python: it owns no storage and depends only on the standard
library, so it can be unit-tested without Rhine-Vault or the HTTP server.

Two render modes are provided:

- sandbox (omniscient): every event, effect and world fact is visible;
- novel (limited perspective): only events witnessed or experienced by one
  viewpoint character appear, so the story can be read like an immersive
  novel instead of a simulation dashboard.
"""

from __future__ import annotations

import copy
import json
import os
import random
import re
import zlib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


EVENT_KINDS = ["相遇", "冲突", "秘密", "失去", "背叛", "结盟", "发现", "威胁", "回归", "平静", "了结"]

GENRE_WEIGHTS: dict[str, dict[str, int]] = {
    "奇幻": {"发现": 4, "威胁": 4, "相遇": 3, "秘密": 2, "平静": 1},
    "科幻": {"发现": 4, "威胁": 4, "秘密": 2, "失去": 2, "相遇": 2},
    "悬疑": {"秘密": 5, "威胁": 3, "发现": 3, "背叛": 2, "平静": 1},
    "都市": {"冲突": 3, "秘密": 2, "结盟": 2, "相遇": 3, "平静": 2},
    "历史": {"冲突": 3, "结盟": 3, "回归": 2, "秘密": 2, "平静": 1},
    "爱情": {"相遇": 4, "结盟": 2, "平静": 2, "失去": 2, "秘密": 1},
    "轻小说": {"相遇": 3, "结盟": 3, "平静": 3, "发现": 2, "秘密": 1},
}
DEFAULT_WEIGHTS = {kind: 2 for kind in EVENT_KINDS}
DEFAULT_WEIGHTS["了结"] = 0

ACT_PLAN = [
    {"act": "序幕", "turns": (1, 5), "tension": (25, 40)},
    {"act": "发展", "turns": (6, 12), "tension": (40, 60)},
    {"act": "转折", "turns": (13, 18), "tension": (60, 78)},
    {"act": "高潮", "turns": (19, 24), "tension": (75, 92)},
    {"act": "尾声", "turns": (25, 999), "tension": (25, 50)},
]

ACT_BIASES = {
    0: {"相遇": 2, "平静": 2, "秘密": 1},
    1: {"冲突": 2, "秘密": 2, "发现": 2},
    2: {"背叛": 2, "威胁": 3, "失去": 2},
    3: {"冲突": 3, "威胁": 3, "背叛": 1},
    4: {"平静": 3, "结盟": 2, "发现": 1},
}

ACT_BEATS = {
    0: [("关系", "关系萌芽"), ("秘密", "秘密浮现")],
    1: [("冲突", "冲突升级"), ("伏笔", "伏笔回收")],
    2: [("转折", "重大转折"), ("真相", "真相揭露")],
    3: [("对决", "最终对决")],
    4: [("结局", "结局落定")],
}

GENRE_ENDING_KINDS = {
    "悬疑": "真相大白",
    "奇幻": "守护与封印",
    "科幻": "远航",
    "爱情": "携手同行",
    "历史": "尘埃落定",
    "都市": "重获日常",
    "轻小说": "新的开始",
}

QUALITY_GUIDE = (
    "写作质量要求：1) 用具体的感官细节（视觉、听觉、触觉、气味）代替空泛形容；"
    "2) 心理描写要有层次，避免直白贴标签；"
    "3) 对话自然，符合人物身份与说话风格；"
    "4) 长短句交替，控制叙事节奏；"
    "5) 段落留白，避免流水账；"
    "6) 避免 AI 腔（慎用“仿佛、不禁、然而、不禁让人”等套话）；"
    "7) 与已知设定、人物声音、时间线严格一致，不发明未发生的情节。"
)

GUIDANCE_KIND_KEYWORDS: dict[str, str] = {
    "背叛": "背叛",
    "结盟": "结盟",
    "联盟": "结盟",
    "同盟": "结盟",
    "冲突": "冲突",
    "吵架": "冲突",
    "战斗": "冲突",
    "威胁": "威胁",
    "危险": "威胁",
    "秘密": "秘密",
    "发现": "发现",
    "相遇": "相遇",
    "见面": "相遇",
    "失去": "失去",
    "回归": "回归",
    "平静": "平静",
}

SECRETS = [
    "钟楼每晚零点都会多敲一下",
    "那封没有署名的信其实来自过去",
    "城里失踪的人都曾在同一个晚上回来过",
    "记录本最后一页写着主角的名字",
    "那场大火掩盖了一个真正的身份",
    "地图背面有一行永远擦不掉的字",
    "旧码头下埋着一扇不该存在的门",
]

INNER_THOUGHTS = {
    "相遇": "这个人的出现，不是偶然。",
    "冲突": "事情不该走到这一步。",
    "秘密": "这里有什么不对劲。",
    "失去": "有些东西再也回不来了。",
    "背叛": "信任正在碎裂。",
    "结盟": "可以相信他们吗？",
    "发现": "原来如此。",
    "威胁": "危险正在靠近。",
    "回归": "旧事重提。",
    "平静": "平静得让人不安。",
    "了结": "总该有个了结。",
}

ROLE_KEYWORDS = ["主角", "主人公", "主人"]
FACTION_KEYWORDS = ["势力", "派系", "家族", "王国", "公会", "组织", "王朝", "教会"]


@dataclass
class CastMember:
    id: str
    name: str
    role: str = "配角"
    drive: str = "完成自己的目标"
    fear: str = "失去重要之物"
    stance: str = "中立"
    alive: bool = True
    relations: dict[str, int] = field(default_factory=dict)
    identity: str = ""
    traits: list[str] = field(default_factory=list)
    background: str = ""
    location: str = ""
    secret: str = ""
    abilities: list[str] = field(default_factory=list)
    weakness: str = ""
    last_turn: int = 0


@dataclass
class Faction:
    id: str
    name: str
    attitude: int = 0


@dataclass
class WorldState:
    locations: list[str] = field(default_factory=list)
    factions: list[Faction] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    tension: int = 30
    connections: list[list[str]] = field(default_factory=list)


@dataclass
class PlotThread:
    id: str
    title: str
    kind: str = "主线"
    status: str = "active"
    seed_turn: int = 1
    resolve_turn: int | None = None
    participants: list[str] = field(default_factory=list)
    secret: str = ""


@dataclass
class BranchOption:
    id: str
    label: str
    hint: str
    effects: dict[str, Any] = field(default_factory=dict)


@dataclass
class BranchChoice:
    question: str
    options: list[BranchOption] = field(default_factory=list)


@dataclass
class EvolutionEvent:
    id: str
    turn: int
    kind: str
    title: str
    summary: str
    participants: list[str] = field(default_factory=list)
    witnesses: list[str] = field(default_factory=list)
    location: str = ""
    effects: dict[str, Any] = field(default_factory=dict)
    branch: BranchChoice | None = None
    chosen_option_id: str | None = None
    chosen_option_label: str | None = None


@dataclass
class EvolutionSettings:
    chaos: int = 45
    branch_frequency: int = 35
    events_per_turn: int = 1
    auto_resolve: bool = False


@dataclass
class PlanBeat:
    id: str
    title: str
    kind: str
    status: str = "pending"
    due_turn: int = 0
    event_id: str = ""


@dataclass
class StoryArc:
    act_index: int = 0
    act_name: str = "序幕"
    tension_range: list[int] = field(default_factory=lambda: [25, 40])
    ending_kind: str = ""
    beats: list[PlanBeat] = field(default_factory=list)


@dataclass
class EvolutionState:
    project_id: str
    project_name: str = ""
    genre: str = "未分类"
    seed: int = 0
    turn: int = 0
    clock: int = 0
    cast: list[CastMember] = field(default_factory=list)
    world: WorldState = field(default_factory=WorldState)
    threads: list[PlotThread] = field(default_factory=list)
    history: list[EvolutionEvent] = field(default_factory=list)
    pending_branch: BranchChoice | None = None
    pending_event: EvolutionEvent | None = None
    ending: str = ""
    settings: EvolutionSettings = field(default_factory=EvolutionSettings)
    updated_at: str = ""
    ai_prose: dict[str, str] = field(default_factory=dict)
    guidance: str = ""
    arc: StoryArc = field(default_factory=StoryArc)


@dataclass
class TurnResult:
    turn: int
    advanced: bool = False
    awaiting_branch: bool = False
    branch: BranchChoice | None = None
    events: list[EvolutionEvent] = field(default_factory=list)
    prose: str = ""
    message: str = ""
    ending: str = ""


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def _extract_snippet(content: str, markers: tuple[str, ...], fallback: str) -> str:
    text = str(content or "").strip()
    for marker in markers:
        index = text.find(marker)
        if index >= 0:
            snippet = text[index : index + 30].splitlines()[0].strip()
            if snippet:
                return snippet
    return fallback


def _parse_traits(raw: Any) -> list[str]:
    if isinstance(raw, list):
        items = [str(item).strip() for item in raw]
    else:
        items = re.split(r"[，,、;；\n]+", str(raw or ""))
    return [item for item in items if item][:8]


def _relation_score(relation_text: Any) -> int:
    text = str(relation_text or "")
    if any(word in text for word in ("恋人", "挚友", "家人", "伴侣", "死党", "知己")):
        return 2
    if any(word in text for word in ("朋友", "同伴", "盟友", "同事", "搭档")):
        return 1
    if any(word in text for word in ("敌人", "仇人", "死敌", "宿敌")):
        return -2
    if any(word in text for word in ("对手", "竞争者", "讨厌", "不和", "疏远")):
        return -1
    return 0


def _cast_from_characters(characters: list[dict[str, Any]]) -> list[CastMember]:
    members: list[CastMember] = []
    for index, raw in enumerate(characters):
        item_id = str(raw.get("id") or f"character-{index + 1}")
        name = str(raw.get("name") or raw.get("title") or f"角色{index + 1}").strip() or f"角色{index + 1}"
        content = str(raw.get("content") or "")
        role_raw = str(raw.get("role") or "").strip()
        role = role_raw or ("主角" if index == 0 or any(keyword in name for keyword in ROLE_KEYWORDS) else "配角")
        status = str(raw.get("status") or "").strip()
        alive = not any(word in status for word in ("死亡", "已死", "阵亡", "身亡"))
        members.append(
            CastMember(
                id=item_id,
                name=name,
                role=role,
                drive=str(raw.get("drive") or "").strip()
                or _extract_snippet(content, ("想要", "渴望", "目标是", "目标", "希望"), "完成自己的目标"),
                fear=str(raw.get("fear") or "").strip()
                or _extract_snippet(content, ("害怕", "恐惧", "担心", "怕"), "失去重要之物"),
                stance=str(raw.get("stance") or "中立").strip() or "中立",
                alive=alive,
                identity=str(raw.get("identity") or "").strip(),
                traits=_parse_traits(raw.get("traits")),
                background=str(raw.get("background") or "").strip(),
                location="",
                secret=str(raw.get("secret") or "").strip(),
                abilities=_parse_traits(raw.get("abilities")),
                weakness=str(raw.get("weakness") or "").strip(),
            )
        )
    by_name = {member.name: member.id for member in members}
    for member, raw in zip(members, characters):
        for relation in raw.get("relationships") or []:
            if not isinstance(relation, dict):
                continue
            relation_name = str(relation.get("name") or "").strip()
            target_id = by_name.get(relation_name)
            if not target_id or target_id == member.id:
                continue
            member.relations[target_id] = max(-2, min(2, _relation_score(relation.get("relation"))))
    if not members:
        members.append(CastMember(id="auto-protagonist", name="主人公", role="主角"))
    return members


def _world_from_items(world: list[dict[str, Any]]) -> WorldState:
    locations: list[str] = []
    facts: list[str] = []
    factions: list[Faction] = []
    for raw in world:
        title = str(raw.get("name") or raw.get("title") or "").strip()
        kind = str(raw.get("type") or "").strip()
        content = str(raw.get("details") or raw.get("content") or "").strip()
        summary = str(raw.get("summary") or "").strip()
        description = summary or content
        fact_text = f"{title}：{description[:120]}" if description else title
        if not title:
            continue
        if kind in {"势力", "组织", "王国", "家族"} or any(keyword in title for keyword in FACTION_KEYWORDS):
            factions.append(Faction(id=f"faction-{len(factions) + 1}", name=title))
        elif kind in {"地点", ""}:
            locations.append(title)
        if description and len(facts) < 8:
            facts.append(fact_text)
    if not locations:
        locations = ["故事开始的地方"]
    if not factions:
        factions = [Faction(id="faction-1", name="未知势力")]
    return WorldState(locations=locations[:6], factions=factions, facts=facts, tension=30)


def _assign_cast_locations(state: EvolutionState) -> None:
    locations = state.world.locations or ["故事开始的地方"]
    for index, member in enumerate(state.cast):
        member.location = locations[index % len(locations)]


def _initial_threads(state: EvolutionState) -> list[PlotThread]:
    threads = [
        PlotThread(
            id="thread-main-1",
            title=f"{state.project_name or '这个故事'}的核心悬念",
            kind="主线",
            participants=[state.cast[0].id] if state.cast else [],
        )
    ]
    if len(state.cast) >= 2:
        threads.append(
            PlotThread(
                id="thread-rel-1",
                title=f"{state.cast[0].name}与{state.cast[1].name}的关系",
                kind="情感",
                participants=[state.cast[0].id, state.cast[1].id],
            )
        )
    for member in state.cast:
        if member.secret:
            threads.append(
                PlotThread(
                    id=f"thread-secret-{member.id}",
                    title=f"{member.name}的秘密",
                    kind="伏笔",
                    participants=[member.id],
                    secret=member.secret,
                )
            )
    return threads


def needs_new_character(state: EvolutionState) -> bool:
    alive = [member for member in state.cast if member.alive]
    return len(alive) < 3 and state.turn >= 3


def suggested_character(state: EvolutionState) -> dict[str, str]:
    roles = ["配角", "盟友", "恋人", "反派"]
    used_roles = {member.role for member in state.cast}
    role = next((item for item in roles if item not in used_roles), "配角")
    return {"role": role, "drive": "寻找自己在故事中的位置"}


def add_character_to_run(state: EvolutionState, character: dict[str, Any]) -> CastMember:
    member = _cast_from_characters([character])[0]
    member.last_turn = 0
    locations = state.world.locations or ["故事开始的地方"]
    member.location = locations[len(state.cast) % len(locations)]
    state.cast.append(member)
    if member.secret:
        state.threads.append(
            PlotThread(
                id=f"thread-secret-{member.id}",
                title=f"{member.name}的秘密",
                kind="伏笔",
                participants=[member.id],
                secret=member.secret,
            )
        )
    return member


def start_run(
    project_id: str,
    project_name: str = "",
    genre: str = "未分类",
    characters: list[dict[str, Any]] | None = None,
    world: list[dict[str, Any]] | None = None,
    map_nodes: list[dict[str, Any]] | None = None,
    map_edges: list[dict[str, Any]] | None = None,
    settings: EvolutionSettings | None = None,
    seed: int | None = None,
) -> EvolutionState:
    """Create a new evolution run from story project data."""
    resolved_seed = int(seed) if seed is not None else zlib.crc32(str(project_id or "").encode("utf-8"))
    state = EvolutionState(
        project_id=project_id,
        project_name=project_name,
        genre=genre or "未分类",
        seed=resolved_seed,
        cast=_cast_from_characters(characters or []),
        world=_world_from_items(world or []),
        settings=copy.deepcopy(settings) if settings is not None else EvolutionSettings(),
    )
    if map_nodes:
        node_names = [
            str(node.get("name") or "").strip()
            for node in map_nodes
            if str(node.get("name") or "").strip()
        ]
        if node_names:
            state.world.locations = node_names
    if map_edges:
        id_to_name = {
            str(node.get("id") or ""): str(node.get("name") or "").strip()
            for node in map_nodes or []
        }
        connections: list[list[str]] = []
        for edge in map_edges:
            first = id_to_name.get(str(edge.get("from") or ""))
            second = id_to_name.get(str(edge.get("to") or ""))
            if first and second and first != second and [first, second] not in connections:
                connections.append([first, second])
        state.world.connections = connections
    _assign_cast_locations(state)
    state.threads = _initial_threads(state)
    state.arc = StoryArc(
        act_index=0,
        act_name=ACT_PLAN[0]["act"],
        tension_range=list(ACT_PLAN[0]["tension"]),
        ending_kind=GENRE_ENDING_KINDS.get(genre or "", "尘埃落定"),
        beats=[
            PlanBeat(id=f"beat-0-{kind}", title=title, kind=kind, due_turn=1)
            for kind, title in ACT_BEATS[0]
        ],
    )
    return state


def evolution_settings_from_dict(raw: dict[str, Any] | None) -> EvolutionSettings:
    allowed = {item.name for item in fields(EvolutionSettings)}
    return EvolutionSettings(
        **{key: value for key, value in (raw or {}).items() if key in allowed and isinstance(value, (int, float, bool))}
    )


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _member(state: EvolutionState, member_id: str) -> CastMember | None:
    for member in state.cast:
        if member.id == member_id:
            return member
    return None


def _member_name(state: EvolutionState, member_id: str) -> str:
    member = _member(state, member_id)
    return member.name if member else member_id


def _pick_primary(state: EvolutionState, rng: random.Random) -> CastMember:
    alive = [member for member in state.cast if member.alive]
    pool = alive or state.cast
    min_turn = min((member.last_turn for member in pool), default=0)
    rotated = [member for member in pool if member.last_turn <= min_turn + 2]
    weighted: list[CastMember] = []
    for member in rotated or pool:
        weight = 3 if member.role == "主角" else 2
        weighted.extend([member] * weight)
    return rng.choice(weighted)


def _pick_secondary(state: EvolutionState, rng: random.Random, primary: CastMember) -> CastMember | None:
    candidates = [member for member in state.cast if member.alive and member.id != primary.id]
    if not candidates:
        return None
    related = [
        member
        for member in candidates
        if abs(primary.relations.get(member.id, 0)) >= 1 or abs(member.relations.get(primary.id, 0)) >= 1
    ]
    return rng.choice(related or candidates)


def _pick_location(
    state: EvolutionState,
    rng: random.Random,
    primary: CastMember | None = None,
) -> str:
    if primary is not None and primary.location:
        neighbors: list[str] = []
        for pair in state.world.connections:
            if pair[0] == primary.location:
                neighbors.append(pair[1])
            elif pair[1] == primary.location:
                neighbors.append(pair[0])
        if neighbors:
            return rng.choice(neighbors)
    return rng.choice(state.world.locations or ["故事开始的地方"])


def _pick_faction(state: EvolutionState) -> Faction | None:
    if state.world.factions:
        return state.world.factions[0]
    return None


def _open_foreshadows(state: EvolutionState) -> list[PlotThread]:
    return [thread for thread in state.threads if thread.kind == "伏笔" and thread.status == "active"]


def _dormant_threads(state: EvolutionState) -> list[PlotThread]:
    return [thread for thread in state.threads if thread.status == "dormant"]


def _pick_foreshadow(state: EvolutionState, rng: random.Random) -> PlotThread | None:
    pool = _open_foreshadows(state)
    return rng.choice(pool) if pool else None


def _pick_dormant(state: EvolutionState, rng: random.Random) -> PlotThread | None:
    pool = _dormant_threads(state)
    return rng.choice(pool) if pool else None


# ---------------------------------------------------------------------------
# Event planning
# ---------------------------------------------------------------------------

def _current_act(state: EvolutionState) -> dict[str, Any]:
    for index, act in enumerate(ACT_PLAN):
        if state.turn <= act["turns"][1]:
            return {**act, "index": index}
    return {**ACT_PLAN[-1], "index": len(ACT_PLAN) - 1}


def _mature_conflict_threads(state: EvolutionState) -> list[PlotThread]:
    return [
        thread
        for thread in state.threads
        if thread.kind == "冲突" and thread.status == "active" and state.turn - thread.seed_turn >= 4
    ]


def _advance_arc(state: EvolutionState) -> dict[str, Any]:
    act = _current_act(state)
    if act["index"] != state.arc.act_index:
        state.arc.act_index = act["index"]
        state.arc.act_name = act["act"]
        state.arc.tension_range = list(act["tension"])
        for kind, title in ACT_BEATS.get(act["index"], []):
            if not any(beat.kind == kind and beat.status == "pending" for beat in state.arc.beats):
                state.arc.beats.append(
                    PlanBeat(id=f"beat-{act['index']}-{kind}", title=title, kind=kind, due_turn=state.turn)
                )
    low, high = act["tension"]
    if state.world.tension < low:
        state.world.tension = min(low + 5, state.world.tension + 3)
    elif state.world.tension > high and act["index"] < 4:
        state.world.tension = max(high, state.world.tension - 2)
    if act["index"] >= 3 and state.world.tension < 60:
        state.world.tension = min(65, state.world.tension + 4)
    return act


def _update_beats_for_event(state: EvolutionState, event: EvolutionEvent) -> None:
    for beat in state.arc.beats:
        if beat.status == "done":
            continue
        done = False
        if beat.kind == "关系":
            done = len(event.participants) >= 2
        elif beat.kind == "秘密":
            done = event.kind == "秘密"
        elif beat.kind == "冲突":
            done = event.kind in {"冲突", "威胁"} and bool(event.effects.get("new_thread"))
        elif beat.kind == "伏笔":
            done = bool(event.effects.get("resolve_thread"))
        elif beat.kind == "转折":
            done = event.kind in {"背叛", "失去"}
        elif beat.kind == "真相":
            done = event.kind in {"发现", "秘密"} and bool(
                event.effects.get("resolve_thread") or event.effects.get("new_fact")
            )
        elif beat.kind == "对决":
            done = event.kind in {"冲突", "威胁", "了结"} and state.world.tension >= 70
        elif beat.kind == "结局":
            done = bool(state.ending)
        if done:
            beat.status = "done"
            beat.event_id = event.id


def _finish_ending_beat(state: EvolutionState) -> None:
    for beat in state.arc.beats:
        if beat.kind == "结局":
            beat.status = "done"
            beat.event_id = beat.event_id or "ending"


def _pick_weighted_kind(state: EvolutionState, rng: random.Random) -> str:
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(GENRE_WEIGHTS.get(state.genre, {}))
    act = _current_act(state)
    for kind, bias in ACT_BIASES.get(act["index"], {}).items():
        weights[kind] = weights.get(kind, 0) + bias
    if state.world.tension >= 60:
        weights["冲突"] += 2
        weights["威胁"] += 1
        weights["平静"] = 0
    elif state.world.tension <= 20:
        weights["平静"] += 2
    if state.settings.chaos >= 70:
        weights["背叛"] += 1
        weights["失去"] += 1
    weights["了结"] = 3 if _mature_conflict_threads(state) else 0
    total = sum(max(0, weight) for weight in weights.values()) or 1
    roll = rng.randrange(total)
    for kind, weight in weights.items():
        if weight <= 0:
            continue
        if roll < weight:
            return kind
        roll -= weight
    return "平静"


def _event_count(state: EvolutionState, rng: random.Random) -> int:
    base = max(1, min(3, int(state.settings.events_per_turn)))
    if state.settings.chaos >= 60 and rng.random() < 0.35:
        base += 1
    return min(3, base)


def _guidance_bias(state: EvolutionState) -> tuple[str | None, list[str]]:
    guidance = (state.guidance or "").strip()
    if not guidance:
        return None, []
    kind = next(
        (candidate for keyword, candidate in GUIDANCE_KIND_KEYWORDS.items() if keyword in guidance),
        None,
    )
    participants = [member.id for member in state.cast if member.name and member.name in guidance]
    return kind, participants


def _plan_event(state: EvolutionState, rng: random.Random) -> EvolutionEvent:
    forced_kind, forced_participants = _guidance_bias(state)
    kind = forced_kind or _pick_weighted_kind(state, rng)
    if forced_participants:
        primary = _member(state, forced_participants[0])
        if primary is None:
            primary = _pick_primary(state, rng)
        secondary = (
            _member(state, forced_participants[1])
            if len(forced_participants) > 1
            else _pick_secondary(state, rng, primary)
        )
    else:
        primary = _pick_primary(state, rng)
        secondary = _pick_secondary(state, rng, primary)
    participants = [primary.id]
    if kind in {"相遇", "冲突", "背叛", "结盟"} and secondary is not None and secondary.id != primary.id:
        participants.append(secondary.id)
    location = _pick_location(state, rng, primary)
    event = EvolutionEvent(
        id=f"event-{state.turn}-{len(state.history) + 1}",
        turn=state.turn,
        kind=kind,
        title="",
        summary="",
        participants=participants,
        witnesses=list(participants),
        location=location,
    )
    bystander_pool = [
        member
        for member in state.cast
        if member.alive and member.id not in event.participants and (rng.random() < 0.25 or any(rel >= 1 for rel in member.relations.values()))
    ]
    if bystander_pool and rng.random() < 0.45:
        event.witnesses.append(rng.choice(bystander_pool).id)
    _decorate_event(state, event, rng)
    return event


def _ensure_relationship_thread(state: EvolutionState, first: CastMember, second: CastMember) -> None:
    pair_ids = {first.id, second.id}
    exists = any(
        thread.kind == "情感" and thread.status in {"active", "dormant"} and pair_ids.issubset(set(thread.participants))
        for thread in state.threads
    )
    if not exists:
        state.threads.append(
            PlotThread(
                id=f"thread-{state.turn}-{len(state.threads) + 1}",
                title=f"{first.name}与{second.name}的关系",
                kind="情感",
                participants=[first.id, second.id],
            )
        )


def _decorate_event(state: EvolutionState, event: EvolutionEvent, rng: random.Random) -> None:
    primary = _member(state, event.participants[0]) if event.participants else None
    secondary = _member(state, event.participants[1]) if len(event.participants) > 1 else None
    a = primary.name if primary else "某人"
    b = secondary.name if secondary else "某人"
    location = event.location or "故事开始的地方"
    effects: dict[str, Any] = {"tension": 0, "relations": {}}

    if event.kind == "相遇" and secondary is not None:
        event.title = f"{a}与{b}相遇"
        event.summary = f"在{location}，{a}与{b}不期而遇，空气里多了几分变化。"
        effects["relations"] = {primary.id: {secondary.id: 1}, secondary.id: {primary.id: 1}}
        effects["tension"] = -3
        _ensure_relationship_thread(state, primary, secondary)
    elif event.kind == "冲突" and secondary is not None:
        event.title = f"{a}与{b}发生冲突"
        event.summary = f"在{location}，{a}与{b}的矛盾终于爆发。"
        effects["relations"] = {primary.id: {secondary.id: -1}, secondary.id: {primary.id: -1}}
        effects["tension"] = 12
    elif event.kind == "秘密":
        secret = rng.choice(SECRETS)
        event.title = "秘密浮出水面"
        event.summary = f"{a}在{location}发现了一个秘密：{secret}。"
        effects["tension"] = 5
        effects["new_thread"] = {
            "title": f"{a}发现的秘密",
            "kind": "伏笔",
            "participants": [primary.id],
            "secret": secret,
        }
    elif event.kind == "失去":
        victim = secondary or primary
        event.title = f"{victim.name}失去了重要的东西"
        event.summary = f"{victim.name}在{location}失去了重要的东西，命运从此改变。"
        if primary is not None and victim.id != primary.id:
            effects["relations"] = {primary.id: {victim.id: -1}}
        effects["tension"] = 8
    elif event.kind == "背叛" and secondary is not None:
        event.title = f"{b}背叛了{a}"
        event.summary = f"在{location}，{b}背叛了{a}。"
        effects["relations"] = {primary.id: {secondary.id: -2}, secondary.id: {primary.id: -2}}
        effects["tension"] = 15
        effects["new_thread"] = {
            "title": f"{a}与{b}的裂痕",
            "kind": "冲突",
            "participants": [primary.id, secondary.id],
        }
    elif event.kind == "结盟" and secondary is not None:
        event.title = f"{a}与{b}结盟"
        event.summary = f"在{location}，{a}与{b}达成了同盟。"
        effects["relations"] = {primary.id: {secondary.id: 2}, secondary.id: {primary.id: 2}}
        effects["tension"] = -5
    elif event.kind == "发现":
        target = _pick_foreshadow(state, rng)
        if target is not None:
            event.title = "伏笔开始回收"
            event.summary = f"{a}在{location}发现了与「{target.title}」有关的线索。"
            effects["resolve_thread"] = target.id
            effects["new_fact"] = f"{a}证实了关于「{target.title}」的猜想。"
            effects["tension"] = -8
        else:
            event.title = f"{a}有了新发现"
            event.summary = f"{a}在{location}发现了一些不寻常的东西。"
            effects["new_fact"] = f"{location}藏着一件尚未解明的怪事。"
            effects["tension"] = -4
    elif event.kind == "威胁":
        faction = _pick_faction(state)
        faction_name = faction.name if faction else "未知势力"
        event.title = f"威胁逼近{location}"
        event.summary = f"{faction_name}的阴影正在逼近{location}，{a}感到不安。"
        effects["tension"] = 12
        effects["new_thread"] = {
            "title": f"来自{faction_name}的威胁",
            "kind": "冲突",
            "participants": [primary.id],
        }
    elif event.kind == "回归":
        target = _pick_dormant(state, rng)
        if target is not None:
            event.title = f"旧事重提：{target.title}"
            event.summary = f"{target.title}再次出现在{a}面前。"
            effects["resolve_thread"] = target.id
            effects["tension"] = -6
        elif secondary is not None:
            event.title = f"故人归来"
            event.summary = f"{a}在{location}重逢了{b}，往事重新涌上心头。"
            effects["relations"] = {primary.id: {secondary.id: 1}, secondary.id: {primary.id: 1}}
            effects["tension"] = -3
        else:
            event.title = "旧日的影子"
            event.summary = f"{a}在{location}看到了一个似曾相识的背影。"
            effects["tension"] = 2
    elif event.kind == "了结":
        mature = _mature_conflict_threads(state)
        target = rng.choice(mature) if mature else None
        if target is not None:
            event.title = f"{target.title}有了结果"
            event.summary = f"在{location}，{target.title}终于走向了结局。"
            event.participants = list(target.participants or event.participants)
            effects["resolve_thread"] = target.id
            effects["new_fact"] = f"{target.title}的纠葛告一段落。"
            effects["tension"] = -12
        else:
            event.title = "暗流暂时平息"
            event.summary = f"{location}的紧张气氛暂时缓和。"
            effects["tension"] = -8
    else:  # 平静
        event.title = f"{location}的平静日子"
        event.summary = f"{location}度过了平静的一天，{a}暂时得以喘息。"
        effects["tension"] = -10
    event.effects = effects


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

def _option(option_id: str, label: str, hint: str, effects: dict[str, Any]) -> BranchOption:
    return BranchOption(id=option_id, label=label, hint=hint, effects=effects)


def _build_branch(event: EvolutionEvent, rng: random.Random) -> BranchChoice:
    kind = event.kind
    primary = event.participants[0] if event.participants else "a"
    secondary = event.participants[1] if len(event.participants) > 1 else "b"

    def relation(delta: int) -> dict[str, Any]:
        if len(event.participants) < 2:
            return {}
        return {primary: {secondary: delta}, secondary: {primary: delta}}

    def thread(title: str, thread_kind: str = "冲突", secret: str = "") -> dict[str, Any]:
        return {"title": title, "kind": thread_kind, "participants": list(event.participants), "secret": secret}

    if kind == "冲突":
        question = f"{'与'.join(event.participants)}的冲突会如何收场？"
        options = [
            _option("reconcile", "和解", "关系缓和，但裂痕不会真正消失。", {"tension": -8, "relations": relation(2)}),
            _option("escalate", "升级", "冲突彻底爆发，局势更加危险。", {"tension": 15, "relations": relation(-2), "new_thread": thread("越演越烈的冲突")}),
            _option("leave", "离开", "一方抽身离去，留下一个未解的结。", {"tension": -5, "new_thread": thread("没有说出口的结", "伏笔", "那场冲突还有下文")}),
        ]
    elif kind == "秘密":
        question = "这个秘密要怎么处理？"
        options = [
            _option("chase", "追查", "越接近真相，危险越大。", {"tension": 8, "new_thread": thread("被追查的秘密", "伏笔", "真相并不止一层")}),
            _option("silence", "沉默", "当作没看见，暂时安全。", {"tension": -3}),
            _option("reveal", "公开", "秘密一旦说出口，就无法收回。", {"tension": 10, "new_fact": "一个秘密被公之于众。"}),
        ]
    elif kind == "背叛":
        question = "面对背叛，会如何选择？"
        options = [
            _option("forgive", "原谅", "关系出现转机，但信任需要重建。", {"tension": -5, "relations": relation(1)}),
            _option("revenge", "复仇", "仇恨会带来新的仇恨。", {"tension": 12, "relations": relation(-2), "new_thread": thread("复仇的漩涡")}),
            _option("endure", "隐忍", "记下这笔账，等待时机。", {"tension": 4, "new_thread": thread("迟来的清算", "伏笔", "忍耐是有限度的")}),
        ]
    elif kind == "失去":
        question = "失去之后，要怎么办？"
        options = [
            _option("recover", "挽回", "不计代价地追回失去的东西。", {"tension": 5, "new_thread": thread("追回失去之物", "伏笔", "代价已经标好了价格")}),
            _option("accept", "接受", "学着带着缺憾继续走下去。", {"tension": -8}),
            _option("resist", "反击", "把愤怒转向夺走它的人。", {"tension": 12, "new_thread": thread("愤怒的反击")}),
        ]
    elif kind == "结盟":
        question = "这份同盟要走到哪一步？"
        options = [
            _option("formal", "正式结盟", "彼此绑定，风险与收益都更大。", {"tension": -6, "relations": relation(2)}),
            _option("reserved", "保留余地", "留一条退路，也留一个疑心。", {"relations": relation(1), "new_thread": thread("同盟里的疑虑", "伏笔", "退路往往通向决裂")}),
            _option("refuse", "拒绝", "宁可独自面对。", {"tension": 4, "relations": relation(-1)}),
        ]
    elif kind == "发现":
        question = "这个发现要告诉谁？"
        options = [
            _option("keep", "独自保守", "秘密留在自己手里。", {"tension": 4, "new_thread": thread("保守的发现", "伏笔", "独享的秘密会发芽")}),
            _option("share", "分享出去", "更多的人知道，也就更难隐藏。", {"tension": -6, "new_fact": "一个发现被分享给了同伴。"}),
            _option("hide", "藏起来", "连自己都假装不知道。", {"new_thread": thread("被藏起的真相", "伏笔", "藏得越深，回响越大")}),
        ]
    elif kind == "威胁":
        question = "危险逼近，如何应对？"
        options = [
            _option("fight", "迎战", "正面冲突，局势会迅速恶化。", {"tension": 14, "new_thread": thread("与威胁的正面冲突")}),
            _option("retreat", "撤退", "保存实力，但代价是失去立足之地。", {"tension": 6, "new_thread": thread("被迫的退路", "伏笔", "退让不会让威胁消失")}),
            _option("ally", "求援", "向他人求助，欠下一份人情。", {"tension": -4, "relations": relation(2)}),
        ]
    else:
        question = "接下来会怎样？"
        options = [
            _option("follow", "顺势而行", "让事情自然发展。", {"tension": -3, "relations": relation(1)}),
            _option("investigate", "追根究底", "主动去查清楚。", {"tension": 6, "new_thread": thread("被追问的真相", "伏笔", "答案藏在更深的地方")}),
            _option("withdraw", "抽身而退", "暂时离开，静观其变。", {"tension": -2, "new_thread": thread("搁置的疑问", "dormant")}),
        ]
    return BranchChoice(question=question, options=options)


def _resolve_option(branch: BranchChoice, choice_id: str | None, rng: random.Random) -> BranchOption:
    if choice_id == "fate" or not choice_id:
        return rng.choice(branch.options)
    for option in branch.options:
        if option.id == choice_id:
            return option
    return rng.choice(branch.options)


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

def _apply_effects(state: EvolutionState, event: EvolutionEvent) -> None:
    effects = event.effects or {}
    tension_delta = int(effects.get("tension") or 0)
    state.world.tension = max(0, min(100, state.world.tension + tension_delta))

    for from_id, targets in (effects.get("relations") or {}).items():
        member = _member(state, str(from_id))
        if member is None:
            continue
        for to_id, delta in targets.items():
            member.relations[str(to_id)] = max(-2, min(2, member.relations.get(str(to_id), 0) + int(delta)))

    new_thread = effects.get("new_thread")
    if isinstance(new_thread, dict):
        state.threads.append(
            PlotThread(
                id=f"thread-{state.turn}-{len(state.threads) + 1}",
                title=str(new_thread.get("title") or "新线索"),
                kind=str(new_thread.get("kind") or "主线"),
                status=str(new_thread.get("status") or "active"),
                seed_turn=state.turn,
                participants=[str(item) for item in (new_thread.get("participants") or [])],
                secret=str(new_thread.get("secret") or ""),
            )
        )

    resolve_id = str(effects.get("resolve_thread") or "")
    if resolve_id:
        for thread in state.threads:
            if thread.id == resolve_id and thread.status in {"active", "dormant"}:
                thread.status = "resolved"
                thread.resolve_turn = state.turn

    fact = str(effects.get("new_fact") or "").strip()
    if fact and fact not in state.world.facts:
        state.world.facts.append(fact)

    for participant_id in event.participants:
        member = _member(state, participant_id)
        if member is not None:
            member.last_turn = state.turn
            if event.location and event.location in state.world.locations:
                member.location = event.location

    cast_change = effects.get("cast_change")
    if isinstance(cast_change, dict):
        member = _member(state, str(cast_change.get("id") or ""))
        if member is not None and "alive" in cast_change:
            member.alive = bool(cast_change["alive"])

    ending = str(effects.get("ending") or "").strip()
    if ending:
        state.ending = ending


def _maybe_death(state: EvolutionState, rng: random.Random) -> None:
    candidates = [member for member in state.cast if member.alive and member.role != "主角"]
    if not candidates or state.world.tension < 70:
        return
    if rng.random() < 0.07:
        victim = rng.choice(candidates)
        victim.alive = False
        state.world.tension = max(0, state.world.tension - 5)


def _maybe_ending(state: EvolutionState, result: TurnResult) -> None:
    if state.ending:
        result.ending = state.ending
        _finish_ending_beat(state)
        return
    act = _current_act(state)
    active_major = [
        thread for thread in state.threads if thread.kind in {"主线", "冲突"} and thread.status == "active"
    ]
    climax_done = any(beat.kind == "对决" and beat.status == "done" for beat in state.arc.beats)
    if act["index"] >= 4 and (climax_done or state.turn >= 26):
        ending_kind = state.arc.ending_kind or "尘埃落定"
        if active_major:
            state.ending = (
                f"在第{state.turn}回合，《{state.project_name or '这个故事'}》迎来了「{ending_kind}」"
                "的阶段性结局；仍有未解的暗流，为续章留白。"
            )
        else:
            state.ending = (
                f"在第{state.turn}回合，《{state.project_name or '这个故事'}》迎来了「{ending_kind}」的结局。"
            )
        result.ending = state.ending
        _finish_ending_beat(state)


# ---------------------------------------------------------------------------
# Turn advancement
# ---------------------------------------------------------------------------

def advance(
    state: EvolutionState,
    settings: EvolutionSettings | None = None,
    choice_id: str | None = None,
) -> tuple[EvolutionState, TurnResult]:
    """Advance the story by one turn.

    Returns a deep copy; the caller's state is never mutated.

    - With no pending branch: rolls events and applies them. The last event
      may become a pending branch (``awaiting_branch=True``).
    - With a pending branch: ``choice_id=None`` returns the waiting state;
      ``choice_id`` resolves it; ``choice_id="fate"`` picks randomly.
    """
    working = copy.deepcopy(state)
    if settings is not None:
        working.settings = copy.deepcopy(settings)
    result = TurnResult(turn=working.turn)
    rng = random.Random(f"{working.seed}:{working.turn}:{1 if working.pending_branch else 0}")

    if working.pending_branch is not None and working.pending_event is not None:
        if choice_id is None and not working.settings.auto_resolve:
            result.awaiting_branch = True
            result.branch = working.pending_branch
            result.message = "故事停在了抉择时刻。"
            return working, result
        if choice_id is None:
            choice_id = "fate"
        option = _resolve_option(working.pending_branch, choice_id, rng)
        event = working.pending_event
        event.chosen_option_id = option.id
        event.chosen_option_label = option.label
        event.effects = copy.deepcopy(option.effects)
        event.summary = f"{event.summary} 故事的走向因此偏向「{option.label}」。"
        event.branch = None
        working.history.append(event)
        working.pending_branch = None
        working.pending_event = None
        _apply_effects(working, event)
        result.events = [event]
        result.advanced = True
        result.message = f"抉择「{option.label}」改变了故事的走向。"
        working.turn += 1
        working.clock += 1
        _advance_arc(working)
        _update_beats_for_event(working, event)
        _maybe_death(working, rng)
        _maybe_ending(working, result)
        result.turn = working.turn
        result.prose = render_sandbox(working)
        return working, result

    working.turn += 1
    working.clock += 1
    planned: list[EvolutionEvent] = []
    for _ in range(_event_count(working, rng)):
        planned.append(_plan_event(working, rng))

    if planned and not working.ending and rng.randrange(100) < working.settings.branch_frequency:
        branch_event = planned[-1]
        branch_event.branch = _build_branch(branch_event, rng)
        working.pending_event = branch_event
        working.pending_branch = branch_event.branch
        for earlier in planned[:-1]:
            working.history.append(earlier)
            _apply_effects(working, earlier)
        if working.settings.auto_resolve:
            option = _resolve_option(working.pending_branch, "fate", rng)
            branch_event.chosen_option_id = option.id
            branch_event.chosen_option_label = option.label
            branch_event.effects = copy.deepcopy(option.effects)
            branch_event.summary = f"{branch_event.summary} 命运的骰子掷向了「{option.label}」。"
            branch_event.branch = None
            working.history.append(branch_event)
            working.pending_branch = None
            working.pending_event = None
            _apply_effects(working, branch_event)
            result.events = planned
            result.message = f"第{working.turn}回合演化完成，命运骰子选择了「{option.label}」。"
            result.advanced = True
        else:
            result.events = planned[:-1]
            result.awaiting_branch = True
            result.branch = branch_event.branch
            result.message = f"第{working.turn}回合出现了一个抉择。"
    else:
        for event in planned:
            working.history.append(event)
            _apply_effects(working, event)
        result.events = planned
        result.advanced = True
        result.message = f"第{working.turn}回合演化完成。"

    if result.advanced:
        _advance_arc(working)
        for event in result.events:
            _update_beats_for_event(working, event)
        _maybe_death(working, rng)
        _maybe_ending(working, result)
    result.turn = working.turn
    result.prose = render_sandbox(working)
    return working, result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _effect_chips(event: EvolutionEvent) -> list[str]:
    chips: list[str] = []
    effects = event.effects or {}
    tension = int(effects.get("tension") or 0)
    if tension:
        chips.append(f"张力 {tension:+d}")
    if effects.get("resolve_thread"):
        chips.append("伏笔回收")
    if effects.get("new_fact"):
        chips.append("新事实")
    if effects.get("new_thread"):
        chips.append("新线索")
    return chips


def render_sandbox(state: EvolutionState) -> str:
    """Omniscient full-world render used by the sandbox view."""
    lines = [
        f"《{state.project_name or '未命名故事'}》演化沙盘 · 第{state.turn}回合 · "
        f"{state.arc.act_name or '序幕'} · 种子 {state.seed}"
    ]
    if state.ending:
        lines.append(f"【尾声】{state.ending}")
    if not state.history:
        lines.append("还没有事件发生。")
    for event in state.history:
        names = "、".join(_member_name(state, participant) for participant in event.participants) or "世界"
        lines.append(f"[{event.kind}] {event.title}（{names}）")
        lines.append(f"  {event.summary}")
        if event.chosen_option_label:
            lines.append(f"  抉择：{event.chosen_option_label}")
        chips = _effect_chips(event)
        if chips:
            lines.append(f"  {' · '.join(chips)}")
    return "\n".join(lines)


def _visible_events(state: EvolutionState, viewpoint_id: str) -> list[EvolutionEvent]:
    return [
        event
        for event in state.history
        if viewpoint_id in event.participants or viewpoint_id in event.witnesses
    ]


def _limited_paragraphs(state: EvolutionState, event: EvolutionEvent, viewpoint_id: str) -> list[str]:
    viewpoint = _member(state, viewpoint_id)
    viewpoint_name = viewpoint.name if viewpoint else "我"
    if viewpoint_id in event.participants:
        paragraph = event.summary
        thought = INNER_THOUGHTS.get(event.kind)
        paragraphs = [paragraph]
        if thought:
            paragraphs.append(f"{viewpoint_name}心想：{thought}")
        if event.chosen_option_label:
            paragraphs.append(f"最终，{viewpoint_name}选择「{event.chosen_option_label}」。")
        return paragraphs
    if viewpoint_id in event.witnesses:
        return [f"{viewpoint_name}远远看见了：{event.summary}"]
    return []


def render_novel(state: EvolutionState, viewpoint_id: str = "") -> dict[str, Any]:
    """Limited-perspective render: only what the viewpoint character knows."""
    viewpoint = _member(state, viewpoint_id) if viewpoint_id else None
    if viewpoint is None:
        viewpoint = state.cast[0] if state.cast else None
    if viewpoint is None:
        return {"viewpoint_id": "", "viewpoint_name": "", "chapters": [], "hidden_events": 0}

    visible = _visible_events(state, viewpoint.id)
    chapters: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for event in visible:
        if current is None or current["turn"] != event.turn:
            current = {"turn": event.turn, "title": f"第{event.turn}回合", "paragraphs": []}
            chapters.append(current)
        current["paragraphs"].extend(_limited_paragraphs(state, event, viewpoint.id))
    if state.ending:
        chapters.append({"turn": state.turn + 1, "title": "尾声", "paragraphs": [state.ending]})
    return {
        "viewpoint_id": viewpoint.id,
        "viewpoint_name": viewpoint.name,
        "chapters": chapters,
        "hidden_events": max(0, len(state.history) - len(visible)),
    }


def viewpoint_options(state: EvolutionState) -> list[dict[str, str]]:
    return [{"id": member.id, "name": member.name} for member in state.cast]


def build_ai_prose_prompt(
    state: EvolutionState,
    viewpoint_id: str = "",
    global_guidance: str = "",
    variation: str = "",
    writing_style: str = "",
    style_card: str = "",
) -> list[dict[str, str]]:
    """Build an OpenAI-compatible chat prompt for the latest evolution turn."""
    viewpoint = _member(state, viewpoint_id) if viewpoint_id else None
    if viewpoint is None:
        viewpoint = state.cast[0] if state.cast else None
    viewpoint_name = viewpoint.name if viewpoint else "主角"
    resolved_viewpoint_id = viewpoint.id if viewpoint else (state.cast[0].id if state.cast else "")
    previous_prose = [
        text
        for _, text in sorted(
            (
                (int(key.split(":")[0]), text)
                for key, text in state.ai_prose.items()
                if ":" in key
                and key.split(":")[0].isdigit()
                and key.endswith(f":{resolved_viewpoint_id}")
            ),
            key=lambda item: item[0],
        )[-2:]
    ]
    cast_lines = [
        (
            f"{member.name}（{member.role}"
            f"{(' · ' + member.identity) if member.identity else ''}）："
            f"欲望={member.drive or '未设定'}，恐惧={member.fear or '未设定'}，所在地={member.location or '未知'}"
        )
        for member in state.cast[:6]
    ]
    latest_events = state.history[-5:]
    event_lines = [
        (
            f"[第{event.turn}回合·{event.kind}] {event.title}：{event.summary}"
            + (f"（抉择：{event.chosen_option_label}）" if event.chosen_option_label else "")
        )
        for event in latest_events
    ]
    system = (
        "你是小说续写引擎。只依据给定的事件与设定写作，不要发明未发生的情节、"
        "未出场的人物或超出已知世界的设定。用第三人称有限视角，侧重心理描写。"
        + (f"文风：{writing_style}。" if writing_style else "")
        + (
            f"\n风格基准（本故事的语感、句式、节奏必须与以下内容保持一致，不得中途变调）：\n{style_card}"
            if style_card
            else ""
        )
        + QUALITY_GUIDE
    )
    user = [
        f"项目：《{state.project_name or '未命名故事'}》",
        f"类型：{state.genre}",
        f"世界观地点：{'、'.join(state.world.locations)}",
        f"已知事实：{'；'.join(state.world.facts[:5]) or '暂无'}",
        f"角色：\n" + "\n".join(cast_lines) if cast_lines else "角色：暂无",
        f"最近发生的事件：\n" + "\n".join(event_lines) if event_lines else "最近发生的事件：暂无",
    ]
    if state.guidance:
        user.append(f"导演指令（必须遵守）：{state.guidance}")
    if global_guidance:
        user.append(f"全局引导（始终遵守）：{global_guidance}")
    if variation:
        user.append(f"重写要求：{variation}")
    if previous_prose:
        user.append(
            "上文（最近两回 AI 正文，续写时保持人物、语气与时间连续性，不要重复）：\n"
            + "\n\n".join(previous_prose)
        )
    user.append("")
    user.append(
        f"请以「{viewpoint_name}」的有限视角，紧接上文续写 300-500 字正文。"
        "只能写该角色亲身经历或亲眼看到的事，其它角色的秘密与私事一律不写。"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user)},
    ]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def evolution_state_to_dict(state: EvolutionState) -> dict[str, Any]:
    return asdict(state)


def _branch_from_dict(data: dict[str, Any] | None) -> BranchChoice | None:
    if not data:
        return None
    options = [
        BranchOption(
            id=str(option.get("id") or ""),
            label=str(option.get("label") or ""),
            hint=str(option.get("hint") or ""),
            effects=copy.deepcopy(option.get("effects") or {}),
        )
        for option in data.get("options") or []
    ]
    return BranchChoice(question=str(data.get("question") or ""), options=options)


def _event_from_dict(data: dict[str, Any]) -> EvolutionEvent:
    allowed = {item.name for item in fields(EvolutionEvent)}
    payload = {key: value for key, value in data.items() if key in allowed and key != "branch"}
    payload["branch"] = _branch_from_dict(data.get("branch"))
    return EvolutionEvent(**payload)


def evolution_state_from_dict(data: dict[str, Any]) -> EvolutionState:
    settings = EvolutionSettings(
        **{
            key: value
            for key, value in (data.get("settings") or {}).items()
            if key in {item.name for item in fields(EvolutionSettings)} and isinstance(value, (int, float, bool))
        }
    )
    world_raw = data.get("world") or {}
    world = WorldState(
        locations=[str(item) for item in (world_raw.get("locations") or [])],
        factions=[
            Faction(
                id=str(faction.get("id") or f"faction-{index}"),
                name=str(faction.get("name") or "未知势力"),
                attitude=int(faction.get("attitude") or 0),
            )
            for index, faction in enumerate(world_raw.get("factions") or [])
        ],
        facts=[str(item) for item in (world_raw.get("facts") or [])],
        tension=max(0, min(100, int(world_raw.get("tension") or 30))),
        connections=[
            [str(pair[0]), str(pair[1])]
            for pair in (world_raw.get("connections") or [])
            if isinstance(pair, (list, tuple)) and len(pair) == 2
        ],
    )
    cast = [
        CastMember(
            id=str(member.get("id") or f"character-{index}"),
            name=str(member.get("name") or "角色"),
            role=str(member.get("role") or "配角"),
            drive=str(member.get("drive") or "完成自己的目标"),
            fear=str(member.get("fear") or "失去重要之物"),
            stance=str(member.get("stance") or "中立"),
            alive=bool(member.get("alive", True)),
            relations={str(key): int(value) for key, value in (member.get("relations") or {}).items()},
            identity=str(member.get("identity") or ""),
            traits=[str(trait) for trait in (member.get("traits") or []) if str(trait)],
            background=str(member.get("background") or ""),
            location=str(member.get("location") or ""),
            secret=str(member.get("secret") or ""),
            abilities=[str(ability) for ability in (member.get("abilities") or []) if str(ability)],
            weakness=str(member.get("weakness") or ""),
            last_turn=int(member.get("last_turn") or 0),
        )
        for index, member in enumerate(data.get("cast") or [])
    ]
    threads = [
        PlotThread(
            id=str(thread.get("id") or f"thread-{index}"),
            title=str(thread.get("title") or "线索"),
            kind=str(thread.get("kind") or "主线"),
            status=str(thread.get("status") or "active"),
            seed_turn=int(thread.get("seed_turn") or 1),
            resolve_turn=int(thread["resolve_turn"]) if thread.get("resolve_turn") is not None else None,
            participants=[str(item) for item in (thread.get("participants") or [])],
            secret=str(thread.get("secret") or ""),
        )
        for index, thread in enumerate(data.get("threads") or [])
    ]
    arc_raw = data.get("arc") or {}
    arc = StoryArc(
        act_index=int(arc_raw.get("act_index") or 0),
        act_name=str(arc_raw.get("act_name") or ACT_PLAN[0]["act"]),
        tension_range=[int(value) for value in (arc_raw.get("tension_range") or ACT_PLAN[0]["tension"])],
        ending_kind=str(arc_raw.get("ending_kind") or ""),
        beats=[
            PlanBeat(
                id=str(beat.get("id") or f"beat-{index}"),
                title=str(beat.get("title") or "节拍"),
                kind=str(beat.get("kind") or "其他"),
                status=str(beat.get("status") or "pending"),
                due_turn=int(beat.get("due_turn") or 0),
                event_id=str(beat.get("event_id") or ""),
            )
            for index, beat in enumerate(arc_raw.get("beats") or [])
        ],
    )
    return EvolutionState(
        project_id=str(data.get("project_id") or ""),
        project_name=str(data.get("project_name") or ""),
        genre=str(data.get("genre") or "未分类"),
        seed=int(data.get("seed") or 0),
        turn=int(data.get("turn") or 0),
        clock=int(data.get("clock") or 0),
        cast=cast,
        world=world,
        threads=threads,
        history=[_event_from_dict(event) for event in (data.get("history") or [])],
        pending_branch=_branch_from_dict(data.get("pending_branch")),
        pending_event=_event_from_dict(data["pending_event"]) if data.get("pending_event") else None,
        ending=str(data.get("ending") or ""),
        settings=settings,
        updated_at=str(data.get("updated_at") or ""),
        ai_prose={str(key): str(value) for key, value in (data.get("ai_prose") or {}).items()},
        guidance=str(data.get("guidance") or ""),
        arc=arc,
    )


def turn_result_to_dict(result: TurnResult) -> dict[str, Any]:
    return {
        "turn": result.turn,
        "advanced": result.advanced,
        "awaiting_branch": result.awaiting_branch,
        "branch": asdict(result.branch) if result.branch else None,
        "events": [asdict(event) for event in result.events],
        "prose": result.prose,
        "message": result.message,
        "ending": result.ending,
    }


# ---------------------------------------------------------------------------
# Disk store
# ---------------------------------------------------------------------------

def sanitize_project_id(project_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(project_id or "project"))
    return safe or "project"


class EvolutionStore:
    """Filesystem store for evolution runs (Lore-owned; never touches Vault)."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _path(self, project_id: str) -> Path:
        return self.directory / f"{sanitize_project_id(project_id)}.evolution.json"

    def save(self, state: EvolutionState) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(state.project_id)
        payload = {"format": "rhine-lore-evolution-v1", "state": evolution_state_to_dict(state)}
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)
        return path

    def load(self, project_id: str) -> EvolutionState | None:
        path = self._path(project_id)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return evolution_state_from_dict(payload.get("state") or payload)

    def delete(self, project_id: str) -> bool:
        path = self._path(project_id)
        if path.is_file():
            path.unlink()
            return True
        return False

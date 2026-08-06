# Evolution Sandbox (演化沙盘)

## Goal

Let a story project evolve itself turn by turn so it can be watched like a
sandbox simulation and read like a novel with a limited viewpoint. The writer
can intervene at branch moments, or let the world run on its own.

## Boundary

- Evolution state is owned by Rhine-Lore and saved under `data/projects/`.
- It never reads or mutates Rhine-Vault data and never auto-approves story
  facts. Approved knowledge integration stays on the existing proposal path.
- The engine is deterministic pure Python: same seed + same choices = same
  story. It must not depend on wall-clock randomness or LLM output.

## Engine (`src/rhine_lore/engine.py`)

Core types:

- `CastMember` — name, role, drive, fear, alive, relation scores (-2..2).
- `WorldState` — locations, factions, facts, tension (0..100).
- `PlotThread` — main / character / romance / conflict / foreshadowing, with
  `active` / `dormant` / `resolved` status and a `secret` for foreshadowing.
- `EvolutionEvent` — kind, participants, witnesses, effects, optional branch.
- `BranchChoice` / `BranchOption` — player or fate-decided turning points.
- `EvolutionState` — the full run, JSON-serializable via `to_dict/from_dict`.

Turn loop (`advance`):

1. New turn: pick 1-3 events weighted by genre, tension and chaos.
2. Events are decorated with titles, summaries and effects (tension deltas,
   relation deltas, new threads, foreshadowing seeds, fact discoveries).
3. The last planned event may become a pending branch. With no choice the
   turn waits; `choice_id` resolves it; `"fate"` picks randomly.
4. Effects are applied, rare character death may occur at high tension, and an
   ending may be detected once major threads are resolved after turn 20.

Renders:

- `render_sandbox` — omniscient event log plus world/thread/choice chips.
- `render_novel` — limited-perspective chapters; only events where the
  viewpoint character participates or witnesses appear. `hidden_events` counts
  what the reader does not see.

## API (`/lore-api/evolution/*`)

- `GET /lore-api/evolution/state?project_id=...&viewpoint_id=...`
- `POST /lore-api/evolution/start` — create a run from project characters/world.
- `POST /lore-api/evolution/advance` — `choice_id` (option id / `"fate"`).
- `POST /lore-api/evolution/reset` — delete the run.

Every response contains `state`, `sandbox`, `novel`, `viewpoints`, and the
latest `result`.

## UI

The `演化` activity has:

- Start card: seed, chaos, branch frequency, fate-dice setting.
- Control console: sandbox/novel toggle, manual turn, auto-play speed, reset.
- Branch banner with option hints and the fate dice.
- Sandbox: event timeline, world state, threads/foreshadowing, cast relations.
- Novel: viewpoint selector, limited-perspective reader, "接收进正文".

## Verification

```powershell
python -m unittest discover -s tests
cd ui
npm run build
python main.py
```

Open `http://127.0.0.1:8786/` -> 演化. Browser QA of the full page and the
auto-play timer remains the open acceptance boundary; API behavior and the
deterministic engine are covered by 16 focused tests.

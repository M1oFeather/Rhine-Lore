# Rhine-Lore

> A friendly writing studio with optional audited knowledge support.

Rhine-Lore is a standalone writing workspace for story projects, worldbuilding,
character notes, creative conversation, and long-form chapter editing.

Rhine-Lore owns editor and project state. Rhine-Vault remains the canonical
audited knowledge backend for approved world facts, Context Bundles, review
state, snapshots, and long-term retrieval.

## Features

- Story project dashboard stored locally in the browser.
- Guided story creation with a lightweight name, genre, and one-line idea form;
  the first chapter is prepared automatically.
- Project import, export, and duplication for browser-local story backups.
- The active story and chapter are restored after a page refresh.
- Worldbuilding, character, outline, timeline, foreshadowing, and chapter
  work areas.
- Structured character cards: identity, role, drive, fear, personality tags,
  appearance, background, relationship web, and current status. The cards
  seed the evolution sandbox and can be synced to the knowledge library as
  formatted proposals.
- Detailed character editor with a simplified/full view toggle, plus extra
  fields (age, stance, abilities, weakness, secret, speech style).
- Structured worldbuilding cards (location, faction, rule, history, item,
  legend) with one-click placement onto the story map.
- A story map: drag location nodes, draw connections between them, zoom, and
  edit place descriptions. Map nodes become evolution locations, characters
  are assigned starting locations, and events move participants along
  connected routes.
- Conversation-based drafting tied to the active story project and chapter.
- Conversation messages and chapter excerpts can be saved as story reference
  material without exposing backend workflow terms.
- A productized knowledge intake page for manual reference drafts, chapter
  extraction, review staging, approval, and one-click chat references.
- A novel reader/editor page with chapter navigation, formatted reading view,
  character count, chapter progress, auto-save status, and long-form text
  editing.
- An evolution sandbox that advances the story itself turn by turn: characters
  meet, clash, ally, uncover secrets, and betray; the world tension rises and
  falls. Branch moments can be decided by the player or by the "fate dice",
  and an auto-play mode lets the world run on its own.
- A limited-perspective novel view that only shows what one viewpoint
  character personally experienced or witnessed, with one-click acceptance of
  the evolution record into the manuscript.
- Deterministic evolution runs: every run has a seed, so the same seed plus
  the same choices always produces the same story. Runs are saved locally
  under `data/projects/`.
- Simple writing-first entry points, with backend and AI-related details kept in
  settings and advanced settings.
- A four-item mobile navigation bar for the workbench, conversation, manuscript,
  and reference library; detailed story setup remains available from the
  workbench.
- Candidate knowledge submission through `POST /api/manual`.
- Approved reference lookup through `POST /api/context`.
- Default Rhine-Vault Core startup, optional Vault Web installation, and
  external local Vault connection.
- Local proxy for same-origin browser calls to a local Rhine-Vault backend.
- Optional local Rhine-Vault launcher in Settings so non-technical writers can
  deploy their own knowledge backend from a checkout path.

## Project Structure

```text
Rhine-Lore/
├─ README.md
├─ pyproject.toml
├─ main.py
├─ src/
│  └─ rhine_lore/
│     ├─ core.py
│     ├─ engine.py                  # deterministic story evolution engine
│     └─ server.py
├─ ui/                           # Vite + Vue + Element Plus primary UI
│  ├─ src/
│  │  ├─ api.ts
│  │  ├─ App.vue
│  │  ├─ main.ts
│  │  └─ styles.css
├─ web/                          # dependency-free fallback UI
├─ docs/
│  ├─ architecture/
│  └─ implementation/
├─ tests/
└─ data/
```

## Start

```powershell
python main.py
```

Or double-click `start.bat` at the project root to launch with the same
settings in a visible console.

The app defaults to binding every local interface (`0.0.0.0`), so it is
reachable from other devices on the same local network:

```text
本机:    http://127.0.0.1:8786/
局域网:  http://<电脑局域网IP>:8786/
```

The console prints the exact LAN address on startup. If a phone cannot open
it, allow Python through Windows Defender Firewall for private networks, or
run locally only with `python main.py --host 127.0.0.1`.

On startup Rhine-Lore tries to bring up the default Rhine-Vault Core for its
own workspace. Port `8765` is intentionally not used because common local
tools (for example the Blender MCP host) bind it; Lore tries `8795`, then
`8796`, then `8797` automatically:

```text
http://127.0.0.1:8795/
```

The default Core checkout is the sibling `Rhine-Vault` project, and the default
database lives under `data/rhine-vault-core.db`. If that checkout is missing,
Rhine-Lore still opens and shows the Vault status in Settings.

`main.py` serves `ui/dist` when it exists. If the Element UI has not been built,
it falls back to the dependency-free `web/` workspace.


## Rhine-Vault Integration

Rhine-Lore has three Vault paths:

- Default Core: started automatically from the default local checkout when
  available.
- Vault Web: installable from Lore Settings when the Vault checkout contains
  `ui/package.json`, then opened through the Vault URL.
- External Vault: connected by pasting a local Vault Web/API URL or by setting
  host and port.

Open `设置 -> 高级设置 -> Rhine-Vault` to adjust:

- `Rhine-Vault 项目路径`: a local checkout containing `main.py`;
- `主机` / `端口`: local bind target, usually `127.0.0.1:8795`;
- `数据库路径`: SQLite database path, defaulting to Rhine-Lore's `data/`;
- `Python 解释器`: optional, otherwise Rhine-Lore prefers the Vault checkout's
  `.venv\Scripts\python.exe` and falls back to the current Python runtime.

The launcher only starts a fixed local command, never an arbitrary shell command.
The normal `/api/*` calls proxy to the selected local Vault URL.

## Evolution Sandbox

Open the `演化` activity for any story project to create an evolution run:

- The engine advances the story one turn at a time. Event choices are shaped
  by the genre, character drives, world tension, and the chaos setting.
- At branch moments you can pick an option or roll the "fate dice"; in
  auto-play mode branches resolve themselves and the world keeps moving.
- The sandbox view shows every event, world state, plot threads, open
  foreshadowing, and character relations. The novel view only renders what
  the selected viewpoint character knows, so the story can be read as an
  immersive limited-perspective novel.
- Evolution runs are Lore-owned local files (`data/projects/*.evolution.json`);
  they never enter the Rhine-Vault approval workflow. "接收进正文" appends the
  current evolution record to the active chapter.
- The engine is deterministic pure Python and works offline. Real-LLM prose
  expansion through the Vault OpenAI-compatible endpoint is a future switch;
  conversation drafting still uses the offline FakeLLM by default.

### AI 正文扩写

工作台首页的「AI 生成通道」可以直接配置（DeepSeek / OpenAI / 自定义预设，
默认 DeepSeek：`https://api.deepseek.com/v1` + `deepseek-chat`）。API Key
仅保存在浏览器 localStorage，经本机 Vault 转发，不写入磁盘。配置后：

- 演化页“小说”视图的“AI 扩写当前回合”会把最近事件和角色/世界观信息组成
  场景简报，生成 300-500 字的有限视角正文，可编辑并一键追加进章节；
- 对话创作的“发送”改用真实模型续写/讨论（未配置时仍为离线 FakeLLM 兜底）。

未配置时演化与创作完全可用，正文使用本地模板。

## Frontend

Rhine-Lore follows the Rhine-Vault frontend architecture:

- Vite + Vue 3 + Element Plus under `ui/`;
- typed API helper functions in `ui/src/api.ts`;
- a single shell in `ui/src/App.vue`;
- shared activity-sidebar, topbar, workspace, and run-output layout patterns;
- `/api` proxied to Rhine-Vault in both Vite dev mode and the local Python
  server.

```powershell
cd ui
npm install
npm run build
```

## Development Checks

```powershell
python -m unittest discover -s tests
```

## Boundary

Rhine-Lore does not import private Rhine-Vault Python modules, read the
Rhine-Vault SQLite database directly, or mutate approved Markdown files. It uses
public HTTP APIs and submits durable story facts as proposals for explicit
review.


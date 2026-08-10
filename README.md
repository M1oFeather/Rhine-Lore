# Rhine-Lore

> A friendly writing studio with optional audited knowledge support.

Rhine-Lore is a standalone writing workspace for story projects, worldbuilding,
character notes, creative conversation, and long-form chapter editing.

Rhine-Lore owns editor and project state. Rhine-Vault remains the canonical
audited knowledge backend for approved world facts, Context Bundles, review
state, snapshots, and long-term retrieval.

## Features

- Story project dashboard stored locally in the browser.
- Automatic disk backup: every project save is mirrored to
  `data/projects/<project-id>.project.json` after a short debounce. If the
  browser storage is cleared, the workbench shows a “从磁盘恢复” entry with a
  backup list; restoring keeps the same project id, so the on-disk evolution
  run reconnects automatically.
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
- Map editing is fully interactive: drag nodes (with pointer capture so it
  never drops), click a connection to select and delete it, edit the selected
  node's name/description, and jump straight from the evolution sandbox's
  world-state tab to the map editor.
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

The app also shows the current LAN address in 设置 → 常用设置（“局域网访问”），
由服务端 `/lore-api/lan` 实时返回；`start.bat` 显式以 `--host 0.0.0.0` 启动，
保证每次都对局域网开放。

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
保存在服务端磁盘（`data/llm-config.json`），所有设备（本机、局域网手机）
共用同一份配置；浏览器不再持有密钥，生成请求统一经本机 Vault 转发。配置后：

- 演化页“小说”视图的“AI 扩写当前回合”会把最近事件和角色/世界观信息组成
  场景简报，生成 300-500 字的有限视角正文，可编辑并一键追加进章节；
- 对话创作的“发送”改用真实模型续写/讨论（未配置时仍为离线 FakeLLM 兜底）。
- 演化回合默认自动扩写：每推进一回合，配置过 Key 时自动为当前视角生成
  该回合正文并存入演化存档（`ai_prose`），小说视图直接显示 AI 文本并带
  「AI」标记；模板正文只在未配置或生成失败时兜底。控制台可以关闭
  「AI 扩写」开关，切回模板。
- 小说视图是连续阅读：所有回合正文连成一整篇故事，不再按回合分卡片；
  AI 续写时会把最近两回正文作为上文，保证人物、语气和时间连续。
- 演化小说按章阅读：每 4 个回合自动成章（第一章、第二章……），顶部章节
  列表可点击跳转，阅读区与正文页一致——章节标题、回合/幕信息、可调字号、
  上一章/下一章导航；章内正文连续，AI 扩写按视角自动覆盖对应回合。
- 连载阅读模式：读完最后一章点击「生成下一章」，服务端一次推进 4 个回合并
  按当前视角写完本章 AI 正文；可在输入框填写「引导下一章」（临时写入演化
  引导）；「重新生成本章」基于本章事件、前文与全局引导换一种写法重写整章。
- 单章长度可设置：演化小说阅读页可选择每章 2 / 3 / 4 / 6 / 8 个回合，
  按项目保存；章节分组与「生成下一章」都按该长度推进。
- 全局引导：故事档案里可以为整个故事设置一条贯穿始终的方向（例如“保持校园
  日常基调，百合线缓慢推进，伏笔必须回收”），会进入演化正文、章节生成、
  章节重写、演化对话与正文修订的全部提示词。
- 预设选项：演化启动提供 平静 / 标准 / 混乱 难度预设；引导与全局引导旁有
  一键填入的常用方向（制造冲突、推进感情线、回收伏笔、引入新角色等）；
  世界观标签和角色性格标签按类型提供可点击预设 chips（已选中的会高亮）；
  演化对话提供快捷提问。
- 引导功能：控制台输入“导演指令”（例如“让沈砚背叛林澈”），会偏置下一回合
  的事件类型与参与角色，并作为指令进入 AI 正文；不清空则持续生效。
- 长期故事视野：演化按五幕弧线推进（序幕 → 发展 → 转折 → 高潮 → 尾声），
  每幕有目标张力区间与里程碑节拍（关系萌芽、秘密浮现、冲突升级、伏笔回收、
  重大转折、真相揭露、最终对决、结局落定）；角色按参与轮次轮转不冷落；
  成熟超过 4 回合的冲突线索会被“了结”事件回收；到尾声阶段按类型走向结局
  （悬疑→真相大白、奇幻→守护与封印等），未解的暗流会留作续章。沙盘的
  「故事弧线」面板展示当前幕、目标张力、结局方向与节拍完成情况。
- 角色不足提示：存活角色少于 3 个且故事进行到第 3 回合后，控制台会出现
  “故事需要新面孔”提示，可一键打开弹窗创建角色卡（角色、欲望、秘密），
  同时写入项目角色卡与演化存档，秘密自动成为伏笔。
- 与故事对话：演化页新增「对话」视图，可像聊天一样问局势、要建议、下指令；
  对话基于当前幕、张力、线索、角色与最近事件，用户消息可一键「设为引导」。
  状态面板改为页签式（故事弧线 / 世界状态 / 线索伏笔 / 角色状态），布局更紧凑。

### 对话调整正文与一致性评估

对话创作页切换到「调整正文」模式，输入修改意图（例如“把林薇改成从小认识
陈栩”）。AI 会对照全部章节、角色卡、世界观与演化活跃伏笔，输出：

- 修订预览：原文 / 修订后对照，确认后一键应用到对应章节；
- 整体影响评估：发现的「冲突 / 误区 / 不一致 / 提醒」逐条列出依据与处理建议，
  应用修订后自动进入项目的“待处理项”列表；
- 待处理项：对话侧栏可查看、标记已处理 / 忽略 / 删除，随项目导出导入。

该功能必须配置 AI 通道（首页或右上角 AI 面板）。

未配置时演化与创作完全可用，正文使用本地模板。旧的浏览器 localStorage
配置不会自动迁移，请在任意设备上重新填写一次，之后全局域网共享。

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


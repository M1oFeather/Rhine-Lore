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
- Conversation-based drafting tied to the active story project and chapter.
- Conversation messages and chapter excerpts can be saved as story reference
  material without exposing backend workflow terms.
- A productized knowledge intake page for manual reference drafts, chapter
  extraction, review staging, approval, and one-click chat references.
- A novel reader/editor page with chapter navigation, formatted reading view,
  character count, chapter progress, auto-save status, and long-form text
  editing.
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

The app defaults to:

```text
http://127.0.0.1:8786/
```

On startup Rhine-Lore tries to bring up the default Rhine-Vault Core for its own
workspace:

```text
http://127.0.0.1:8765/
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
- `主机` / `端口`: local bind target, usually `127.0.0.1:8765`;
- `数据库路径`: SQLite database path, defaulting to Rhine-Lore's `data/`;
- `Python 解释器`: optional, otherwise Rhine-Lore prefers the Vault checkout's
  `.venv\Scripts\python.exe` and falls back to the current Python runtime.

The launcher only starts a fixed local command, never an arbitrary shell command.
The normal `/api/*` calls proxy to the selected local Vault URL.

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


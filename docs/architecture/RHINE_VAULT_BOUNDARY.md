# Rhine-Vault Boundary

Rhine-Lore is a client product. It connects to Rhine-Vault through public HTTP
APIs and keeps the knowledge authority split intact.

## Owned By Rhine-Lore

- story projects;
- volumes, chapters, scenes, and drafts;
- worldbuilding and character editor state;
- timeline, outline, foreshadowing, and payoff planning;
- manuscript export presets;
- local model and UI preferences.

## Owned By Rhine-Vault

- approved MemoryNode records;
- Capture Proposal, Staging, and Approval workflow;
- Context Bundle generation;
- retrieval profiles and graph projection;
- snapshots, imports, audit, and backend management.

## First-Milestone API Surface

- `GET /api/health`
- `GET /api/workspaces`
- `POST /api/workspaces`
- `POST /api/manual`
- `GET /api/proposals`
- `POST /api/proposals/{proposal_id}/stage`
- `GET /api/staging`
- `POST /api/staging/approve`
- `GET /api/nodes`
- `POST /api/context`
- `GET /api/graph/local`
- `POST /api/documents/generate`

## Explicit Non-Goals

- No direct SQLite reads.
- No direct Markdown mutation.
- No private Rhine-Vault Python imports.
- No automatic approval of story facts.
- No dependency on removed `/api/novel/*` or `/novel` routes.


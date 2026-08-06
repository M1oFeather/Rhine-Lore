# First Milestone

The first Rhine-Lore milestone is a frontend-first writing workspace connected
to a local Rhine-Vault backend. The primary frontend now follows the
Rhine-Vault `ui/` architecture: Vite, Vue 3, Element Plus, typed API helpers,
activity sidebar, topbar, main workspace, and run-output panel.

## Included

- connection settings;
- story project list and project detail workspace;
- worldbuilding and character note editors;
- chapter list and chapter editor;
- conversation-based drafting for the active chapter;
- a novel reading/editing page with formatted preview and manuscript editing;
- approved Context Bundle sidebar;
- candidate knowledge submission;
- proposal and staging status panels.
- `/api` proxy behavior matching Rhine-Vault dev UI.

## Verification

```powershell
python -m unittest discover -s tests
cd ui
npm run build
python main.py
```

Open `http://127.0.0.1:8786/` and configure the Rhine-Vault backend URL.

# Style Adoption

## Project

- Name: Rhine-Lore
- Repository: `Rhine-Lore`
- Current status: first standalone workspace scaffold

## Adopted

- [x] Project-facing `README.md`
- [x] Root `main.py`
- [x] Clear package under `src/rhine_lore`
- [x] `docs`, `conf`, `data`, `tests`, and `web` split
- [x] Rhine-Vault-style `ui/` frontend architecture
- [x] Runtime data ignored
- [x] Basic test command
- [x] Deterministic evolution engine with disk-backed runs
- [x] Evolution sandbox and limited-perspective novel views

## Deferred

- Local product database is deferred; browser local storage is enough for the
  first writing workspace slice. Evolution runs are the first disk-backed
  Lore-owned state (`data/projects/`).

## Next

1. Add persistent local project storage.
2. Add richer manuscript export.
3. Add deterministic consistency and foreshadowing checks.
4. Browser-QA the evolution page and auto-play loop end to end.
5. Optional real-LLM prose expansion through the Vault OpenAI-compatible
   endpoint, with the template writer as offline fallback.

# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Two services: `backend/` (FastAPI + SQLModel/Postgres) and `frontend/` (Next.js App Router). See the root `README.md` for how to run both locally.
- There is no user auth anywhere in this product. Spotify access is server-side only, via the Client Credentials flow (app-level token, no login) in `backend/app/spotify_client.py`. This was a deliberate captain decision: Spotify's Development Mode caps a new app at 5 logged-in users with no realistic path to more for a solo project, so personalized login was dropped entirely.
- Spotify's `audio-features`/`audio-analysis` endpoints are gone for any app registered after 2024-11-27. There is no first-party energy/valence/danceability data available, and `preview_url` is frequently null/unpredictable per track.
- The per-track vibe/energy pipeline (`backend/app/vibe_analysis.py` + `backend/app/vibe_service.py`) computes its own approximate signal from 30-second preview clips using librosa, not Spotify's data and not Essentia - see the docstring at the top of `vibe_analysis.py` for why Essentia's pretrained mood classifiers weren't used (no model weights ship with the pip package; running them needs a separate runtime download this repo doesn't vendor). Results are cached in Postgres by Spotify track ID (`TrackVibe` model) so a track is only ever analyzed once, even across different albums/playlists. A track with no analyzable preview gets `vibe: null` in `/api/lookup` rather than failing the request.
- Backend tests never call the real Spotify API - they mock `httpx` calls with `respx` (see `backend/tests/`). Keep it that way; live credentials should never be required to run the test suite. Vibe-pipeline tests likewise mock `download_preview_clip`/`analyze_audio` rather than hitting the network; `backend/tests/fixtures/tiny_clip.wav` is a tiny checked-in fixture for the one test that runs real librosa analysis.
- The backend test suite runs against an in-memory SQLite engine (`DATABASE_URL=sqlite:///:memory:`, set in `backend/tests/conftest.py`), not Postgres. `backend/app/database.py`'s `get_engine()` special-cases in-memory SQLite URLs to use a shared `StaticPool` connection.
- Frontend tests use Vitest + React Testing Library (jsdom), run with `npm test` from `frontend/`. Config is `frontend/vitest.config.mts` / `frontend/vitest.setup.ts`. The setup file polyfills `ResizeObserver` and stubs `HTMLElement` offset dimensions (both needed for Recharts' `ResponsiveContainer` to render in jsdom), and calls RTL's `cleanup()` after each test (not automatic under Vitest). `frontend/app/types.ts` must be kept in sync with `backend/app/schemas.py` by hand - nothing enforces this across the language boundary.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.

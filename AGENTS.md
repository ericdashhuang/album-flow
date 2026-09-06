# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Two services: `backend/` (FastAPI + SQLModel/Postgres) and `frontend/` (Next.js App Router). See the root `README.md` for how to run both locally.
- There is no user auth anywhere in this product. Spotify access is server-side only, via the Client Credentials flow (app-level token, no login) in `backend/app/spotify_client.py`. This was a deliberate captain decision: Spotify's Development Mode caps a new app at 5 logged-in users with no realistic path to more for a solo project, so personalized login was dropped entirely.
- Spotify's `audio-features`/`audio-analysis` endpoints are gone for any app registered after 2024-11-27. There is no first-party energy/valence/danceability data available. Any future "vibe"/energy pipeline needs its own audio-analysis approach (e.g. running your own analysis on preview clips) - it cannot call those endpoints.
- Backend tests never call the real Spotify API - they mock `httpx` calls with `respx` (see `backend/tests/`). Keep it that way; live credentials should never be required to run the test suite.
- The backend test suite runs against an in-memory SQLite engine (`DATABASE_URL=sqlite:///:memory:`, set in `backend/tests/conftest.py`), not Postgres. `backend/app/database.py`'s `get_engine()` special-cases in-memory SQLite URLs to use a shared `StaticPool` connection.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.

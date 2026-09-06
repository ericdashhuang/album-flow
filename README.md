# Album Flow

Paste a Spotify album or playlist link and see its tracklist.
This is the initial scaffold: URL lookup and tracklist display only.
Audio/energy analysis is a separate, later phase.

## Project structure

- `backend/` - FastAPI service that talks to the Spotify Web API (Client Credentials flow, no user login) and exposes `GET /api/lookup`.
- `frontend/` - Next.js (App Router) app with a single page: paste a link, see the tracklist.
- `docker-compose.yml` - local Postgres for backend development.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for local Postgres), or any Postgres instance you point `DATABASE_URL` at.
- A Spotify developer app.
Create one at https://developer.spotify.com/dashboard to get a real `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
Until you have real credentials, the backend runs fine with the placeholder values in `.env.example` - lookups against real Spotify data will just fail with a 502 until real credentials are set.

## Running the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# Edit .env with real Spotify credentials once you have a developer app.

# Start a local Postgres (from the repo root):
docker compose up -d postgres

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`.
Interactive docs are at `http://localhost:8000/docs`.

Run the backend test suite (no live Spotify calls; all HTTP calls are mocked):

```bash
cd backend
pytest
```

## Running the frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The app is now at `http://localhost:3000`.
It expects the backend to be running at the URL in `NEXT_PUBLIC_API_BASE_URL` (`http://localhost:8000` by default).

## Known constraints

- No user login: every visitor gets the same experience against public Spotify albums/playlists.
Spotify's Development Mode quota for new apps makes a personalized-login flow impractical for a solo project.
- Spotify's `audio-features`/`audio-analysis` endpoints are gone for new apps, so this scaffold does not (and cannot) compute an energy/vibe score yet.
That's deliberately a separate, later task.

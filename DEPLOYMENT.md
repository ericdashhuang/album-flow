# Deploying to Render

`render.yaml` at the repo root is a Render Blueprint.
It already defines the backend web service, the frontend web service, the managed Postgres database, and how they're wired together.
This doc covers only what the blueprint cannot automate: creating a Render account, applying the blueprint, and supplying secrets.

## 1. Connect the repo

1. Sign in (or sign up) at [dashboard.render.com](https://dashboard.render.com).
2. Click **New > Blueprint**.
3. Connect your GitHub account if you haven't already, then select `ericdashhuang/album-flow`.
4. Render reads `render.yaml` and shows a preview of the three resources it will create: `album-flow-backend`, `album-flow-frontend`, and `album-flow-db`.

## 2. Apply the blueprint

Click **Apply**. Render provisions the Postgres database first, then builds and deploys both services.
The backend's `DATABASE_URL` is wired automatically from the database resource; you don't need to copy any connection string by hand.

## 3. Fill in the two Spotify secrets

`render.yaml` marks `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` as `sync: false`, so Render will prompt for them during the apply step (or you can set them afterward under `album-flow-backend` > **Environment**).

Get real values from a Spotify developer app at <https://developer.spotify.com/dashboard> (Client Credentials flow only - no redirect URI or user login needed).
Without real values the backend still boots, but any Spotify-backed request fails with a 502.

## 4. Confirm the deploy

Once both services show **Live**:

- Open the backend's health check: `https://album-flow-backend.onrender.com/api/health` should return `{"status": "ok"}`.
- Open the frontend at `https://album-flow-frontend.onrender.com` and start a round to confirm it can reach the backend (check the browser console/network tab if it can't).

## Notes and caveats

- **Free-tier Postgres expires.** A `free`-plan Render Postgres database is deleted 30 days after creation (14-day grace period to upgrade first). Render emails you ahead of both deadlines. Upgrade the `album-flow-db` plan before then if you want to keep the data.
- **Free-tier web services sleep.** Both services are on the `free` plan, which spins down after 15 minutes of inactivity; the first request after a period of idleness will be slow while it spins back up. Upgrade the plan on either service if that's not acceptable.
- **Cross-service URLs are hardcoded, not templated.** Render's blueprint `fromService` reference only exposes a service's private-network host/port, not its public URL, so `render.yaml` hardcodes each service's `https://<name>.onrender.com` URL for the other to call/CORS-allow. If you rename `album-flow-backend` or `album-flow-frontend`, or attach a custom domain to either, update `CORS_ORIGINS` and `NEXT_PUBLIC_API_BASE_URL` in `render.yaml` (or directly in the dashboard) to match.

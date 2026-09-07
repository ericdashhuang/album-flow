import type { GuessResponse, RevealResponse, StartRoundResponse } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiRequestError(
      response.status,
      data.detail ?? "Something went wrong. Please try again."
    );
  }

  return data as T;
}

export function startRound(artistName: string): Promise<StartRoundResponse> {
  return postJson<StartRoundResponse>("/api/game/rounds", { artist_name: artistName });
}

export function submitGuess(roundId: string, albumSpotifyId: string): Promise<GuessResponse> {
  return postJson<GuessResponse>(`/api/game/rounds/${roundId}/guess`, {
    album_spotify_id: albumSpotifyId,
  });
}

export function revealRound(roundId: string, giveUp = false): Promise<RevealResponse> {
  const query = giveUp ? "?give_up=true" : "";
  return postJson<RevealResponse>(`/api/game/rounds/${roundId}/reveal${query}`, {});
}

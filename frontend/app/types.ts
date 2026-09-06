export interface Vibe {
  vibe_score: number;
  energy: number;
  brightness: number;
  tempo_bpm: number;
  source: string;
}

export interface Track {
  spotify_id: string;
  name: string;
  artist: string;
  duration_ms: number;
  track_number: number;
  preview_url: string | null;
  vibe: Vibe | null;
}

export interface LookupResult {
  item_type: "album" | "playlist";
  spotify_id: string;
  name: string;
  owner: string;
  cover_art_url: string | null;
  tracks: Track[];
}

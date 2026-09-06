export interface Track {
  name: string;
  artist: string;
  duration_ms: number;
  track_number: number;
}

export interface LookupResult {
  item_type: "album" | "playlist";
  spotify_id: string;
  name: string;
  owner: string;
  cover_art_url: string | null;
  tracks: Track[];
}

"use client";

import { useState, type FormEvent } from "react";
import Image from "next/image";
import styles from "./page.module.css";
import { formatDuration } from "./format";
import EnergyArcChart from "./EnergyArcChart";
import type { LookupResult } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<LookupResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/lookup?url=${encodeURIComponent(url)}`
      );
      const body = await response.json();

      if (!response.ok) {
        setError(body.detail ?? "Something went wrong looking that up.");
        return;
      }

      setResult(body as LookupResult);
    } catch {
      setError(
        "Couldn't reach the Album Flow backend. Is it running?"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <h1 className={styles.title}>Album Flow</h1>
        <p className={styles.subtitle}>
          Paste a Spotify album or playlist link to see its tracklist.
        </p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <input
            className={styles.input}
            type="text"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://open.spotify.com/album/..."
            aria-label="Spotify album or playlist URL"
            required
          />
          <button className={styles.button} type="submit" disabled={loading}>
            {loading ? "Looking up..." : "Look up"}
          </button>
        </form>

        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}

        {result && (
          <section className={styles.result}>
            <div className={styles.resultHeader}>
              {result.cover_art_url && (
                <Image
                  className={styles.coverArt}
                  src={result.cover_art_url}
                  alt={`${result.name} cover art`}
                  width={160}
                  height={160}
                  unoptimized
                />
              )}
              <div>
                <h2 className={styles.resultTitle}>{result.name}</h2>
                <p className={styles.resultOwner}>{result.owner}</p>
                <p className={styles.resultMeta}>
                  {result.item_type === "album" ? "Album" : "Playlist"} ·{" "}
                  {result.tracks.length} tracks
                </p>
              </div>
            </div>

            <EnergyArcChart tracks={result.tracks} />

            <ol className={styles.trackList}>
              {result.tracks.map((track) => (
                <li
                  key={`${track.track_number}-${track.name}`}
                  className={styles.track}
                >
                  <span className={styles.trackNumber}>
                    {track.track_number}
                  </span>
                  <span className={styles.trackText}>
                    <span className={styles.trackName}>{track.name}</span>
                    <span className={styles.trackArtist}>{track.artist}</span>
                  </span>
                  <span className={styles.trackDuration}>
                    {formatDuration(track.duration_ms)}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        )}
      </main>
    </div>
  );
}

import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import EnergyArcChart, { toChartData } from "./EnergyArcChart";
import type { Track } from "./types";

const tracksWithAGap: Track[] = [
  {
    spotify_id: "track-1",
    name: "Opener",
    artist: "Test Artist",
    duration_ms: 180000,
    track_number: 1,
    preview_url: "https://example.com/preview-1.mp3",
    vibe: {
      vibe_score: 0.72,
      energy: 0.8,
      brightness: 0.6,
      tempo_bpm: 128,
      source: "librosa_fallback",
    },
  },
  {
    spotify_id: "track-2",
    name: "Interlude",
    artist: "Test Artist",
    duration_ms: 60000,
    track_number: 2,
    preview_url: null,
    vibe: null,
  },
  {
    spotify_id: "track-3",
    name: "Closer",
    artist: "Test Artist",
    duration_ms: 210000,
    track_number: 3,
    preview_url: "https://example.com/preview-3.mp3",
    vibe: {
      vibe_score: 0.31,
      energy: 0.25,
      brightness: 0.4,
      tempo_bpm: 90,
      source: "librosa_fallback",
    },
  },
];

describe("toChartData", () => {
  test("maps vibe_score per track and preserves null for tracks with no vibe", () => {
    expect(toChartData(tracksWithAGap)).toEqual([
      { trackNumber: 1, name: "Opener", artist: "Test Artist", vibeScore: 0.72 },
      { trackNumber: 2, name: "Interlude", artist: "Test Artist", vibeScore: null },
      { trackNumber: 3, name: "Closer", artist: "Test Artist", vibeScore: 0.31 },
    ]);
  });
});

describe("EnergyArcChart", () => {
  test("renders the chart when at least one track has a vibe score", () => {
    render(<EnergyArcChart tracks={tracksWithAGap} />);
    expect(screen.getByTestId("energy-arc-chart")).toBeInTheDocument();
  });

  test("shows a fallback message instead of a misleading chart when no track has a vibe score", () => {
    const noPreviewTracks: Track[] = tracksWithAGap.map((track) => ({
      ...track,
      vibe: null,
    }));

    render(<EnergyArcChart tracks={noPreviewTracks} />);

    expect(screen.queryByTestId("energy-arc-chart")).not.toBeInTheDocument();
    expect(
      screen.getByText(/no preview clips were available/i)
    ).toBeInTheDocument();
  });
});

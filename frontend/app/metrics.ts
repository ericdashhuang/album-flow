import type { HintMetric } from "./types";

const NOTE_NAMES = [
  "C",
  "C♯",
  "D",
  "D♯",
  "E",
  "F",
  "F♯",
  "G",
  "G♯",
  "A",
  "A♯",
  "B",
];

export type ChartMetric = HintMetric | "vibe_score";

export const ALL_METRIC_LABELS: Record<ChartMetric, string> = {
  vibe_score: "Vibe score",
  danceability: "Danceability",
  acousticness: "Acousticness",
  instrumentalness: "Instrumentalness",
  speechiness: "Speechiness",
  loudness: "Loudness",
  key: "Key",
};

export const METRIC_LABELS: Record<HintMetric, string> = {
  danceability: "Danceability",
  acousticness: "Acousticness",
  instrumentalness: "Instrumentalness",
  speechiness: "Speechiness",
  loudness: "Loudness",
  key: "Key",
};

export const METRIC_COLORS: Record<ChartMetric, string> = {
  vibe_score: "var(--accent)",
  danceability: "var(--chart-danceability)",
  acousticness: "var(--chart-acousticness)",
  instrumentalness: "var(--chart-instrumentalness)",
  speechiness: "var(--chart-speechiness)",
  loudness: "var(--chart-loudness)",
  key: "var(--chart-key)",
};

/** Each metric now renders on its own chart (one line visible at a time via
 * a toggle), so there's no need to squeeze every metric onto a shared 0-1
 * axis anymore - each gets the y-domain that actually fits its raw values. */
export const METRIC_Y_DOMAIN: Record<ChartMetric, [number, number] | undefined> = {
  vibe_score: [0, 1],
  danceability: [0, 1],
  acousticness: [0, 1],
  instrumentalness: [0, 1],
  speechiness: [0, 1],
  loudness: undefined,
  key: [0, 11],
};

export function formatMetricValue(
  metric: ChartMetric,
  value: number,
  mode: number | null | undefined
): string {
  if (metric === "loudness") {
    return `${value.toFixed(1)} dB`;
  }
  if (metric === "key") {
    const noteName = NOTE_NAMES[Math.round(value) % NOTE_NAMES.length] ?? "?";
    const modeName = mode === 0 ? "minor" : mode === 1 ? "major" : null;
    return modeName ? `${noteName} ${modeName}` : noteName;
  }
  return value.toFixed(2);
}

export function formatMetricAxisTick(metric: ChartMetric, value: number): string {
  if (metric === "key") {
    return NOTE_NAMES[Math.round(value) % NOTE_NAMES.length] ?? "";
  }
  if (metric === "loudness") {
    return `${value.toFixed(0)} dB`;
  }
  return value.toFixed(2);
}

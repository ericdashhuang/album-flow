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

export const METRIC_LABELS: Record<HintMetric, string> = {
  danceability: "Danceability",
  acousticness: "Acousticness",
  instrumentalness: "Instrumentalness",
  speechiness: "Speechiness",
  loudness: "Loudness",
  key: "Key",
};

export const METRIC_COLORS: Record<HintMetric, string> = {
  danceability: "var(--chart-danceability)",
  acousticness: "var(--chart-acousticness)",
  instrumentalness: "var(--chart-instrumentalness)",
  speechiness: "var(--chart-speechiness)",
  loudness: "var(--chart-loudness)",
  key: "var(--chart-key)",
};

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/** Maps a raw metric value onto the chart's shared 0-1 axis. Most metrics are
 * already 0-1; loudness (dB) and key (pitch class 0-11) get rescaled so all
 * lines can share one y-axis - the raw value is still what's shown in the
 * legend/tooltip via formatMetricValue. */
export function normalizeMetricValue(metric: HintMetric, value: number): number {
  if (metric === "loudness") {
    return clamp01((value + 60) / 60);
  }
  if (metric === "key") {
    return clamp01(value / 11);
  }
  return clamp01(value);
}

export function formatMetricValue(
  metric: HintMetric,
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

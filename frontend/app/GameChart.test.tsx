import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import GameChart, { buildChartData } from "./GameChart";
import type { HintPoint, RevealedMetric } from "./types";

const hints: HintPoint[] = [
  { track_number: 1, vibe_score: 0.72 },
  { track_number: 2, vibe_score: null },
  { track_number: 3, vibe_score: 0.31 },
];

const revealedMetrics: RevealedMetric[] = [
  {
    metric: "danceability",
    data: [
      { track_number: 1, value: 0.6, mode: null },
      { track_number: 2, value: null, mode: null },
      { track_number: 3, value: 0.2, mode: null },
    ],
  },
];

describe("buildChartData", () => {
  test("merges base vibe scores with revealed metrics per track number", () => {
    const data = buildChartData(hints, revealedMetrics);

    expect(data).toEqual([
      {
        trackNumber: 1,
        name: undefined,
        vibeScore: 0.72,
        metricValues: { danceability: 0.6 },
        metricModes: { danceability: null },
      },
      {
        trackNumber: 2,
        name: undefined,
        vibeScore: null,
        metricValues: { danceability: null },
        metricModes: { danceability: null },
      },
      {
        trackNumber: 3,
        name: undefined,
        vibeScore: 0.31,
        metricValues: { danceability: 0.2 },
        metricModes: { danceability: null },
      },
    ]);
  });

  test("attaches track names when provided (post-reveal)", () => {
    const data = buildChartData(hints, [], { 1: "Opener", 3: "Closer" });
    expect(data.map((point) => point.name)).toEqual(["Opener", undefined, "Closer"]);
  });
});

describe("GameChart", () => {
  test("renders the chart with just the base vibe-score line", () => {
    render(<GameChart hints={hints} revealedMetrics={[]} />);
    expect(screen.getByTestId("game-chart")).toBeInTheDocument();
    const legend = screen.getByTestId("game-chart-legend");
    expect(legend).toHaveTextContent("Vibe score");
    expect(legend).not.toHaveTextContent("Danceability");
  });

  test("legend grows with each newly revealed metric", () => {
    render(<GameChart hints={hints} revealedMetrics={revealedMetrics} />);
    const legend = screen.getByTestId("game-chart-legend");
    expect(legend).toHaveTextContent("Vibe score");
    expect(legend).toHaveTextContent("Danceability");
  });
});

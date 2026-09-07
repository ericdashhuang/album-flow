import { describe, expect, test } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  test("renders only the base vibe-score toggle when no metric is revealed yet", () => {
    render(<GameChart hints={hints} revealedMetrics={[]} />);
    expect(screen.getByTestId("game-chart")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /vibe score/i })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /danceability/i })).not.toBeInTheDocument();
  });

  test("adds a toggle for each newly revealed metric", () => {
    render(<GameChart hints={hints} revealedMetrics={revealedMetrics} />);
    expect(screen.getByRole("tab", { name: /vibe score/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /danceability/i })).toBeInTheDocument();
  });

  test("shows one metric's line at a time, switching which is active on toggle click", () => {
    render(<GameChart hints={hints} revealedMetrics={revealedMetrics} />);

    const vibeTab = screen.getByRole("tab", { name: /vibe score/i });
    const danceabilityTab = screen.getByRole("tab", { name: /danceability/i });

    expect(vibeTab).toHaveAttribute("aria-selected", "true");
    expect(danceabilityTab).toHaveAttribute("aria-selected", "false");

    fireEvent.click(danceabilityTab);

    expect(danceabilityTab).toHaveAttribute("aria-selected", "true");
    expect(vibeTab).toHaveAttribute("aria-selected", "false");
  });

  test("auto-switches the active tab to a newly revealed metric", async () => {
    const { rerender } = render(<GameChart hints={hints} revealedMetrics={[]} />);
    expect(screen.getByRole("tab", { name: /vibe score/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );

    rerender(<GameChart hints={hints} revealedMetrics={revealedMetrics} />);

    await waitFor(() =>
      expect(screen.getByRole("tab", { name: /danceability/i })).toHaveAttribute(
        "aria-selected",
        "true"
      )
    );
    expect(screen.getByRole("tab", { name: /vibe score/i })).toHaveAttribute(
      "aria-selected",
      "false"
    );
  });

  test("does not auto-switch away from a manually selected tab until a new metric arrives", async () => {
    const { rerender } = render(<GameChart hints={hints} revealedMetrics={revealedMetrics} />);

    // Player manually switches back to vibe score after danceability unlocked.
    fireEvent.click(screen.getByRole("tab", { name: /vibe score/i }));
    expect(screen.getByRole("tab", { name: /vibe score/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );

    // Re-rendering with an equal-length revealedMetrics array (a new
    // reference, but no *new* metric) must not snap the tab back.
    rerender(<GameChart hints={hints} revealedMetrics={[...revealedMetrics]} />);
    expect(screen.getByRole("tab", { name: /vibe score/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
  });
});

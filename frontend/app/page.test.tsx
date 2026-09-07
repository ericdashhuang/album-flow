import { describe, expect, test, vi, type Mock } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import Home from "./page";
import type { GuessResponse, RevealResponse, StartRoundResponse } from "./types";

vi.mock("./api", () => {
  class MockApiRequestError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  }
  return {
    ApiRequestError: MockApiRequestError,
    startRound: vi.fn(),
    submitGuess: vi.fn(),
    revealRound: vi.fn(),
  };
});

import { ApiRequestError, revealRound, startRound, submitGuess } from "./api";

const START_ROUND_RESULT: StartRoundResponse = {
  round_id: "round-1",
  artist_name: "Test Artist",
  album_options: [
    { spotify_id: "album-a", name: "Album A" },
    { spotify_id: "album-b", name: "Album B" },
    { spotify_id: "album-c", name: "Album C" },
  ],
  track_count: 2,
  hints: [
    { track_number: 1, vibe_score: 0.5 },
    { track_number: 2, vibe_score: 0.6 },
  ],
};

const REVEAL_RESULT: RevealResponse = {
  album_name: "Album A",
  album_image_url: null,
  artist_name: "Test Artist",
  tracks: [
    { track_number: 1, name: "Opener Track", vibe_score: 0.5, danceability: 0.4 },
    { track_number: 2, name: "Closer Track", vibe_score: 0.6, danceability: 0.7 },
  ],
  revealed_metrics: ["danceability"],
};

async function startAGame() {
  render(<Home />);
  fireEvent.change(screen.getByLabelText(/artist name/i), {
    target: { value: "Test Artist" },
  });
  fireEvent.click(screen.getByRole("button", { name: /start guessing/i }));
  await screen.findByText("Album A");
}

describe("landing state", () => {
  test("starts a round and shows the album options plus the base chart", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);

    await startAGame();

    expect(screen.getByText("Album B")).toBeInTheDocument();
    expect(screen.getByText("Album C")).toBeInTheDocument();
    expect(screen.getByTestId("game-chart")).toBeInTheDocument();
    expect(screen.getByTestId("game-chart-legend")).toHaveTextContent("Vibe score");
    expect(screen.getByTestId("game-chart-legend")).not.toHaveTextContent("Danceability");
  });

  test("shows a friendly message when the artist has too few albums", async () => {
    (startRound as Mock).mockRejectedValueOnce(
      new ApiRequestError(422, "Test Artist doesn't have enough real studio albums for a round.")
    );

    render(<Home />);
    fireEvent.change(screen.getByLabelText(/artist name/i), {
      target: { value: "Test Artist" },
    });
    fireEvent.click(screen.getByRole("button", { name: /start guessing/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/doesn't have enough real studio albums/i);
  });

  test("shows a friendly message when the artist can't be found", async () => {
    (startRound as Mock).mockRejectedValueOnce(new ApiRequestError(404, "not found"));

    render(<Home />);
    fireEvent.change(screen.getByLabelText(/artist name/i), {
      target: { value: "Nobody" },
    });
    fireEvent.click(screen.getByRole("button", { name: /start guessing/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't find an artist named "Nobody"/i);
  });
});

describe("round state - guessing and hint reveal", () => {
  test("a wrong guess removes that album from the options and increments the count", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock).mockResolvedValueOnce({
      correct: false,
      wrong_guess_count: 1,
      newly_revealed_metric: null,
    } satisfies GuessResponse);

    await startAGame();

    fireEvent.click(screen.getByRole("button", { name: "Album B" }));

    expect(await screen.findByText(/1 wrong guess/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Album B" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Album C" })).toBeInTheDocument();
  });

  test("every 2nd wrong guess reveals the next metric as a new chart line", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock)
      .mockResolvedValueOnce({
        correct: false,
        wrong_guess_count: 1,
        newly_revealed_metric: null,
      } satisfies GuessResponse)
      .mockResolvedValueOnce({
        correct: false,
        wrong_guess_count: 2,
        newly_revealed_metric: {
          metric: "danceability",
          data: [
            { track_number: 1, value: 0.4, mode: null },
            { track_number: 2, value: 0.7, mode: null },
          ],
        },
      } satisfies GuessResponse);

    await startAGame();

    fireEvent.click(screen.getByRole("button", { name: "Album B" }));
    await screen.findByText(/1 wrong guess/i);
    expect(screen.getByTestId("game-chart-legend")).not.toHaveTextContent("Danceability");

    fireEvent.click(screen.getByRole("button", { name: "Album C" }));

    expect(await screen.findByText(/2 wrong guesses/i)).toBeInTheDocument();
    expect(screen.getByTestId("game-chart-legend")).toHaveTextContent("Danceability");
  });

  test("a correct guess moves straight to the reveal state", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock).mockResolvedValueOnce({
      correct: true,
      wrong_guess_count: 0,
      newly_revealed_metric: null,
    } satisfies GuessResponse);
    (revealRound as Mock).mockResolvedValueOnce(REVEAL_RESULT);

    await startAGame();

    fireEvent.click(screen.getByRole("button", { name: "Album A" }));

    expect(await screen.findByText("Opener Track")).toBeInTheDocument();
  });
});

describe("reveal state", () => {
  test("renders track names and a glossary covering every metric shown during the round", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock).mockResolvedValueOnce({
      correct: true,
      wrong_guess_count: 2,
      newly_revealed_metric: null,
    } satisfies GuessResponse);
    (revealRound as Mock).mockResolvedValueOnce(REVEAL_RESULT);

    await startAGame();
    fireEvent.click(screen.getByRole("button", { name: "Album A" }));

    expect(await screen.findByRole("heading", { name: "Album A" })).toBeInTheDocument();
    expect(screen.getByText("Opener Track")).toBeInTheDocument();
    expect(screen.getByText("Closer Track")).toBeInTheDocument();

    const glossary = screen.getByLabelText(/metric glossary/i);
    expect(glossary).toHaveTextContent("Vibe score");
    expect(glossary).toHaveTextContent(/blend of energy and musical positiveness/i);
    expect(glossary).toHaveTextContent("Danceability");
    expect(glossary).toHaveTextContent(/suitable the track is for dancing/i);

    expect(screen.getByRole("button", { name: /play again/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try a different artist/i })).toBeInTheDocument();
  });
});

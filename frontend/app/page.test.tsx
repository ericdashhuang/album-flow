import { afterEach, beforeEach, describe, expect, test, vi, type Mock } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Home from "./page";
import type {
  ArtistSuggestion,
  GuessResponse,
  RevealResponse,
  StartRoundResponse,
} from "./types";

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
    searchArtists: vi.fn().mockResolvedValue([]),
    submitGuess: vi.fn(),
    revealRound: vi.fn(),
  };
});

import { ApiRequestError, revealRound, searchArtists, startRound, submitGuess } from "./api";

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
    expect(screen.getByRole("tab", { name: /energy level/i })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /danceability/i })).not.toBeInTheDocument();
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

  describe("artist autocomplete", () => {
    beforeEach(() => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    const SUGGESTIONS: ArtistSuggestion[] = [
      { spotify_id: "kanye-id", name: "Kanye West", image_url: "https://example.com/kanye.jpg" },
    ];

    test("shows debounced suggestions with images and selecting one starts the round by ID", async () => {
      (searchArtists as Mock).mockResolvedValueOnce(SUGGESTIONS);
      (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);

      render(<Home />);
      fireEvent.change(screen.getByLabelText(/artist name/i), { target: { value: "kan" } });

      // Not called until the debounce window elapses.
      expect(searchArtists).not.toHaveBeenCalled();

      await vi.advanceTimersByTimeAsync(300);
      await waitFor(() => expect(searchArtists).toHaveBeenCalledWith("kan"));

      const suggestion = await screen.findByRole("option", { name: /kanye west/i });
      expect(suggestion.querySelector("img")).toHaveAttribute(
        "src",
        expect.stringContaining("kanye.jpg")
      );

      fireEvent.click(suggestion);

      await waitFor(() =>
        expect(startRound).toHaveBeenCalledWith({
          artistSpotifyId: "kanye-id",
          artistName: "Kanye West",
        })
      );
      await screen.findByText("Album A");
    });
  });
});

describe("round state - guessing and hint reveal", () => {
  test("a wrong guess removes that album from the options and increments the count", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock).mockResolvedValueOnce({
      correct: false,
      wrong_guess_count: 1,
      eliminated_album_ids: ["album-b"],
      newly_revealed_metric: null,
    } satisfies GuessResponse);

    await startAGame();

    fireEvent.click(screen.getByRole("button", { name: "Album B" }));

    expect(await screen.findByText(/1 wrong guess/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Album B" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Album C" })).toBeInTheDocument();
  });

  test("wrong guesses stay eliminated cumulatively across multiple guesses", async () => {
    // Regression: a prior bug rendered eliminated options from only the most
    // recent guess, so an earlier wrong guess reappeared as clickable.
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock)
      .mockResolvedValueOnce({
        correct: false,
        wrong_guess_count: 1,
        eliminated_album_ids: ["album-b"],
        newly_revealed_metric: null,
      } satisfies GuessResponse)
      .mockResolvedValueOnce({
        correct: false,
        wrong_guess_count: 2,
        eliminated_album_ids: ["album-b", "album-c"],
        newly_revealed_metric: null,
      } satisfies GuessResponse);

    await startAGame();

    fireEvent.click(screen.getByRole("button", { name: "Album B" }));
    await screen.findByText(/1 wrong guess/i);

    fireEvent.click(screen.getByRole("button", { name: "Album C" }));
    await screen.findByText(/2 wrong guesses/i);

    expect(screen.queryByRole("button", { name: "Album B" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Album C" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Album A" })).toBeInTheDocument();
  });

  test("every 2nd wrong guess adds a new metric toggle for the chart", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock)
      .mockResolvedValueOnce({
        correct: false,
        wrong_guess_count: 1,
        eliminated_album_ids: ["album-b"],
        newly_revealed_metric: null,
      } satisfies GuessResponse)
      .mockResolvedValueOnce({
        correct: false,
        wrong_guess_count: 2,
        eliminated_album_ids: ["album-b", "album-c"],
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
    expect(screen.queryByRole("tab", { name: /danceability/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Album C" }));

    expect(await screen.findByText(/2 wrong guesses/i)).toBeInTheDocument();
    const danceabilityTab = screen.getByRole("tab", { name: /danceability/i });
    expect(danceabilityTab).toBeInTheDocument();

    // The toggle actually switches which metric is active.
    fireEvent.click(danceabilityTab);
    expect(danceabilityTab).toHaveAttribute("aria-selected", "true");
  });

  test("a correct guess moves straight to the reveal state", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock).mockResolvedValueOnce({
      correct: true,
      wrong_guess_count: 0,
      eliminated_album_ids: [],
      newly_revealed_metric: null,
    } satisfies GuessResponse);
    (revealRound as Mock).mockResolvedValueOnce(REVEAL_RESULT);

    await startAGame();

    fireEvent.click(screen.getByRole("button", { name: "Album A" }));

    expect(await screen.findByText("Opener Track")).toBeInTheDocument();
  });
});

describe("round state - metric glossary panel", () => {
  test("shows the full glossary from round start, marking unrevealed metrics as locked", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);

    await startAGame();

    const glossary = screen.getByLabelText(/metric glossary/i);
    expect(glossary).toHaveTextContent("Energy level");
    expect(glossary).toHaveTextContent("Danceability");
    expect(glossary).toHaveTextContent("Key");
    expect(glossary).toHaveTextContent(/not yet revealed/i);
  });
});

describe("reveal state", () => {
  test("renders track names and a glossary covering every metric shown during the round", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    (submitGuess as Mock).mockResolvedValueOnce({
      correct: true,
      wrong_guess_count: 2,
      eliminated_album_ids: ["album-b", "album-c"],
      newly_revealed_metric: null,
    } satisfies GuessResponse);
    (revealRound as Mock).mockResolvedValueOnce(REVEAL_RESULT);

    await startAGame();
    fireEvent.click(screen.getByRole("button", { name: "Album A" }));

    expect(await screen.findByRole("heading", { name: "Album A" })).toBeInTheDocument();
    expect(screen.getByText("Opener Track")).toBeInTheDocument();
    expect(screen.getByText("Closer Track")).toBeInTheDocument();

    const glossary = screen.getByLabelText(/metric glossary/i);
    expect(glossary).toHaveTextContent("Energy level");
    expect(glossary).toHaveTextContent(/rating of valence and musical positiveness/i);
    expect(glossary).toHaveTextContent("Danceability");
    expect(glossary).toHaveTextContent(/suitable the track is for dancing/i);

    expect(screen.getByRole("button", { name: /play again/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try a different artist/i })).toBeInTheDocument();
  });

  test("marks every metric as revealed once the round is over, even with fewer guesses than metrics", async () => {
    (startRound as Mock).mockResolvedValueOnce(START_ROUND_RESULT);
    // revealed_metrics reflects only what guess-count milestones unlocked mid-round
    // (a single wrong guess here), well short of every metric the game tracks.
    (revealRound as Mock).mockResolvedValueOnce(REVEAL_RESULT);

    await startAGame();
    fireEvent.click(screen.getByRole("button", { name: /give up/i }));

    expect(await screen.findByRole("heading", { name: "Album A" })).toBeInTheDocument();

    const glossary = screen.getByLabelText(/metric glossary/i);
    expect(glossary).not.toHaveTextContent(/not yet revealed/i);
    expect(glossary).toHaveTextContent("Acousticness");
    expect(glossary).toHaveTextContent("Instrumentalness");
    expect(glossary).toHaveTextContent("Speechiness");
    expect(glossary).toHaveTextContent("Loudness");
    expect(glossary).toHaveTextContent("Key");
  });
});

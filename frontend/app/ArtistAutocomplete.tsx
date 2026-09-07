"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { searchArtists } from "./api";
import type { ArtistSuggestion } from "./types";
import styles from "./ArtistAutocomplete.module.css";

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;

interface ArtistAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect: (artist: ArtistSuggestion) => void;
  disabled?: boolean;
}

export default function ArtistAutocomplete({
  value,
  onChange,
  onSelect,
  disabled,
}: ArtistAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<ArtistSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const query = value.trim();
    const requestId = ++requestIdRef.current;

    const timer = setTimeout(async () => {
      if (requestIdRef.current !== requestId) {
        return;
      }
      if (query.length < MIN_QUERY_LENGTH) {
        setSuggestions([]);
        setOpen(false);
        return;
      }
      try {
        const results = await searchArtists(query);
        if (requestIdRef.current === requestId) {
          setSuggestions(results);
          setOpen(results.length > 0);
        }
      } catch {
        if (requestIdRef.current === requestId) {
          setSuggestions([]);
          setOpen(false);
        }
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [value]);

  function handleSelect(artist: ArtistSuggestion) {
    setOpen(false);
    setSuggestions([]);
    onSelect(artist);
  }

  return (
    <div className={styles.wrapper}>
      <input
        className={styles.input}
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setOpen(suggestions.length > 0)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Artist name, e.g. Radiohead"
        aria-label="Artist name"
        autoComplete="off"
        disabled={disabled}
        required
      />
      {open && (
        <ul className={styles.dropdown} role="listbox">
          {suggestions.map((artist) => (
            <li key={artist.spotify_id}>
              <button
                type="button"
                role="option"
                aria-selected="false"
                className={styles.suggestion}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => handleSelect(artist)}
              >
                {artist.image_url ? (
                  <Image
                    src={artist.image_url}
                    alt=""
                    width={32}
                    height={32}
                    unoptimized
                    className={styles.thumbnail}
                  />
                ) : (
                  <span className={styles.thumbnailPlaceholder} aria-hidden="true" />
                )}
                <span>{artist.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

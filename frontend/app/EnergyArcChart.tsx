"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Dot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Track } from "./types";
import styles from "./EnergyArcChart.module.css";

interface ChartPoint {
  trackNumber: number;
  name: string;
  artist: string;
  vibeScore: number | null;
}

export function toChartData(tracks: Track[]): ChartPoint[] {
  return tracks.map((track) => ({
    trackNumber: track.track_number,
    name: track.name,
    artist: track.artist,
    vibeScore: track.vibe?.vibe_score ?? null,
  }));
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: readonly { payload?: ChartPoint }[];
}

function ChartTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const point = payload[0].payload as ChartPoint;

  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipTrack}>
        {point.trackNumber}. {point.name}
      </p>
      <p className={styles.tooltipArtist}>{point.artist}</p>
      <p className={styles.tooltipScore}>
        {point.vibeScore === null
          ? "No preview available"
          : `Vibe score: ${point.vibeScore.toFixed(2)}`}
      </p>
    </div>
  );
}

function GapDot(props: { cx?: number; cy?: number; payload?: ChartPoint }) {
  const { cx, cy, payload } = props;
  if (payload?.vibeScore !== null || cx === undefined || cy === undefined) {
    return null;
  }
  return <Dot cx={cx} cy={cy} r={4} className={styles.gapMarker} />;
}

export default function EnergyArcChart({ tracks }: { tracks: Track[] }) {
  const data = toChartData(tracks);
  const hasAnyVibe = data.some((point) => point.vibeScore !== null);

  if (!hasAnyVibe) {
    return (
      <p className={styles.empty}>
        No preview clips were available to compute an energy arc for this{" "}
        {tracks.length === 1 ? "track" : "set"}.
      </p>
    );
  }

  return (
    <div className={styles.chart} data-testid="energy-arc-chart">
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <defs>
            <linearGradient id="vibeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="trackNumber"
            tick={{ fill: "var(--muted)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            axisLine={{ stroke: "var(--border)" }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: "var(--muted)", fontFamily: "var(--font-mono)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={32}
          />
          <Tooltip content={ChartTooltip} />
          <Area
            type="monotone"
            dataKey="vibeScore"
            stroke="var(--accent)"
            strokeWidth={2}
            fill="url(#vibeFill)"
            connectNulls={false}
            dot={<GapDot />}
            activeDot={{ r: 5, fill: "var(--accent)" }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

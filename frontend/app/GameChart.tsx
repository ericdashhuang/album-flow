"use client";

import {
  CartesianGrid,
  Label,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HintMetric, HintPoint, RevealedMetric } from "./types";
import { formatMetricValue, METRIC_COLORS, METRIC_LABELS, normalizeMetricValue } from "./metrics";
import styles from "./GameChart.module.css";

export interface ChartDataPoint {
  trackNumber: number;
  name?: string;
  vibeScore: number | null;
  metricValues: Partial<Record<HintMetric, number | null>>;
  metricModes: Partial<Record<HintMetric, number | null>>;
}

export function buildChartData(
  hints: HintPoint[],
  revealedMetrics: RevealedMetric[],
  trackNames?: Record<number, string>
): ChartDataPoint[] {
  const points = new Map<number, ChartDataPoint>();

  for (const hint of hints) {
    points.set(hint.track_number, {
      trackNumber: hint.track_number,
      name: trackNames?.[hint.track_number],
      vibeScore: hint.vibe_score,
      metricValues: {},
      metricModes: {},
    });
  }

  for (const revealed of revealedMetrics) {
    for (const point of revealed.data) {
      const existing = points.get(point.track_number);
      if (!existing) continue;
      existing.metricValues[revealed.metric] = point.value;
      existing.metricModes[revealed.metric] = point.mode;
    }
  }

  return Array.from(points.values()).sort((a, b) => a.trackNumber - b.trackNumber);
}

function metricAccessor(metric: HintMetric) {
  return (point: ChartDataPoint): number | null => {
    const raw = point.metricValues[metric];
    return raw === undefined || raw === null ? null : normalizeMetricValue(metric, raw);
  };
}

interface TooltipPayloadEntry {
  dataKey?: string | ((point: ChartDataPoint) => number | null);
  value?: number | null;
  payload?: ChartDataPoint;
}

interface ChartTooltipProps {
  active?: boolean;
  label?: number;
  payload?: readonly TooltipPayloadEntry[];
}

function ChartTooltip({ active, label, payload }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const point = payload[0].payload;
  if (!point) {
    return null;
  }

  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipTrack}>{point.name ?? `Track ${label}`}</p>
      {point.vibeScore !== null && (
        <p className={styles.tooltipRow}>
          <span className={styles.tooltipSwatch} style={{ background: "var(--accent)" }} />
          Vibe score: {point.vibeScore.toFixed(2)}
        </p>
      )}
      {(Object.keys(point.metricValues) as HintMetric[]).map((metric) => {
        const value = point.metricValues[metric];
        if (value === null || value === undefined) {
          return null;
        }
        return (
          <p key={metric} className={styles.tooltipRow}>
            <span className={styles.tooltipSwatch} style={{ background: METRIC_COLORS[metric] }} />
            {METRIC_LABELS[metric]}: {formatMetricValue(metric, value, point.metricModes[metric])}
          </p>
        );
      })}
    </div>
  );
}

interface GameChartProps {
  hints: HintPoint[];
  revealedMetrics: RevealedMetric[];
  trackNames?: Record<number, string>;
}

export default function GameChart({ hints, revealedMetrics, trackNames }: GameChartProps) {
  const data = buildChartData(hints, revealedMetrics, trackNames);

  return (
    <div className={styles.wrapper}>
      <div className={styles.chart} data-testid="game-chart">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 12, right: 16, left: 4, bottom: 24 }}>
            <CartesianGrid stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="trackNumber"
              tickFormatter={(value: number) => `Track ${value}`}
              tick={{ fill: "var(--muted)", fontFamily: "var(--font-mono)", fontSize: 11 }}
              axisLine={{ stroke: "var(--border)" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: "var(--muted)", fontFamily: "var(--font-mono)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={40}
            >
              <Label
                value="Vibe score (0 = mellow, 1 = high-energy)"
                angle={-90}
                position="insideLeft"
                style={{ fill: "var(--muted)", fontSize: 11, textAnchor: "middle" }}
              />
            </YAxis>
            <Tooltip content={<ChartTooltip />} />
            <Line
              type="monotone"
              dataKey="vibeScore"
              name="Vibe score"
              stroke="var(--accent)"
              strokeWidth={2}
              dot={{ r: 3, fill: "var(--accent)" }}
              activeDot={{ r: 5 }}
              connectNulls={false}
              isAnimationActive={false}
            />
            {revealedMetrics.map((entry) => (
              <Line
                key={entry.metric}
                type="monotone"
                dataKey={metricAccessor(entry.metric)}
                name={METRIC_LABELS[entry.metric]}
                stroke={METRIC_COLORS[entry.metric]}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <ul className={styles.legend} data-testid="game-chart-legend">
        <li className={styles.legendItem}>
          <span className={styles.legendSwatch} style={{ background: "var(--accent)" }} />
          Vibe score
        </li>
        {revealedMetrics.map((entry) => (
          <li key={entry.metric} className={styles.legendItem}>
            <span
              className={styles.legendSwatch}
              style={{ background: METRIC_COLORS[entry.metric] }}
            />
            {METRIC_LABELS[entry.metric]}
          </li>
        ))}
      </ul>
    </div>
  );
}

import { HINT_METRIC_ORDER, METRIC_DESCRIPTIONS, type HintMetric } from "./types";
import { ALL_METRIC_LABELS } from "./metrics";
import styles from "./MetricGlossary.module.css";

const ALL_METRICS: (HintMetric | "vibe_score")[] = ["vibe_score", ...HINT_METRIC_ORDER];

interface MetricGlossaryProps {
  /** Metrics unlocked so far this round. Omit (or pass all of them) once the
   * round is over - every metric is always listed, this only controls the
   * "not yet revealed" treatment while a round is in progress. */
  revealedMetrics: HintMetric[];
}

export default function MetricGlossary({ revealedMetrics }: MetricGlossaryProps) {
  const revealedSet = new Set(revealedMetrics);

  return (
    <aside className={styles.panel} aria-label="Metric glossary">
      <h3 className={styles.title}>Metric glossary</h3>
      <dl className={styles.list}>
        {ALL_METRICS.map((metric) => {
          const unlocked = metric === "vibe_score" || revealedSet.has(metric);
          return (
            <div key={metric} className={unlocked ? styles.itemUnlocked : styles.itemLocked}>
              <dt className={styles.term}>
                {ALL_METRIC_LABELS[metric]}
                {!unlocked && <span className={styles.lockedBadge}>Not yet revealed</span>}
              </dt>
              <dd className={styles.description}>{METRIC_DESCRIPTIONS[metric]}</dd>
            </div>
          );
        })}
      </dl>
    </aside>
  );
}

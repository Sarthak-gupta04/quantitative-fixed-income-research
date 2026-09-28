"use client";

import { useState } from "react";
import type { RegimePeriod } from "@/types/data";
import { fmtPct } from "@/lib/formatters";

export default function RegimeSequence({ periods }: { periods: RegimePeriod[] }) {
  const [selected, setSelected] = useState(0);
  const period = periods[selected];

  if (!period) return null;
  const shortLabel = (item: RegimePeriod) => item.label.match(/^\d{4}(?:-\d{4})?/)?.[0]?.replace("-", "–") ?? item.label;

  return (
    <div className="regime-explorer">
      <div className="regime-selector" role="group" aria-label="Historical period">
        {periods.map((item, index) => (
          <button
            className={index === selected ? "regime-choice active" : "regime-choice"}
            type="button"
            key={item.id}
            aria-pressed={index === selected}
            onClick={() => setSelected(index)}
          >
            <span className="regime-choice-index">{String(index + 1).padStart(2, "0")}</span>
            {shortLabel(item)}
          </button>
        ))}
      </div>

      <article className="regime-focus" aria-live="polite">
        <div className="regime-focus-heading">
          <div>
            <span className="mini-label">Selected historical window</span>
            <h3>{shortLabel(period)}</h3>
          </div>
          <p>{period.label.includes("most recent completed calendar year") && <>Most recent completed calendar year<br /></>}{period.actual_start_date} → {period.actual_end_date}</p>
        </div>
        <div className="regime-returns">
          <div><span className="mini-label">Strategy return</span><strong className="number">{fmtPct(period.strategy_return)}</strong></div>
          <div><span className="mini-label">AGG return</span><strong className="number">{fmtPct(period.benchmark_return)}</strong></div>
        </div>
        <dl className="regime-facts">
          <div><dt>Strategy volatility</dt><dd>{fmtPct(period.strategy_annualized_volatility)}</dd></div>
          <div><dt>Maximum drawdown</dt><dd>{fmtPct(period.strategy_maximum_drawdown)}</dd></div>
          <div><dt>Average SHY allocation</dt><dd>{fmtPct(period.average_allocation.SHY)}</dd></div>
          <div><dt>Fully defensive trading days</dt><dd>{fmtPct(period.defensive_shy_allocation.fully_defensive_fraction)}</dd></div>
        </dl>
      </article>
    </div>
  );
}

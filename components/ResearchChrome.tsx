"use client";

import { useEffect, useRef, useState } from "react";
import { fmtDate, fmtPct } from "@/lib/formatters";
import { ASSETS, ASSET_COLORS } from "@/lib/research-view";
import { useResearch } from "@/components/ResearchExperience";

const chapters = [
  { id: "overview", title: "Overview", sections: [["overview", "Introduction"], ["at-a-glance", "Research in 30 seconds"]] },
  { id: "signal", title: "Strategy", sections: [["signal", "The signal"], ["curve", "Treasury curve"], ["risk", "Risk lens"], ["portfolio", "Implementation"]] },
  { id: "decision", title: "Explore", sections: [["decision", "Historical explorer"], ["rate-shock", "Rate shock lab"]] },
  { id: "performance", title: "Evidence", sections: [["performance", "Performance"], ["risk-path", "Risk through time"], ["pressure", "Failure modes"], ["regimes", "Historical episodes"], ["robustness", "Configuration comparison"], ["holdout", "Holdout"], ["current-state", "Latest saved state"]] },
  { id: "method", title: "Method", sections: [["method", "Methodology"], ["provenance", "Provenance & glossary"], ["limitations", "Limitations"], ["references", "References"]] },
];
const sections = chapters.flatMap(c => c.sections);

export function ChapterNav() {
  const [active, setActive] = useState("overview");
  const [progress, setProgress] = useState(0);
  const [open, setOpen] = useState(false);
  const { share, shareStatus } = useResearch();
  useEffect(() => {
    const update = () => {
      let current = "overview";
      // DOM order, rather than chapter order, decides the active section.
      document.querySelectorAll<HTMLElement>("main section[id]").forEach(section => {
        if (section.getBoundingClientRect().top <= window.innerHeight * .3) current = section.id;
      });
      setActive(current);
      const length = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(length > 0 ? Math.min(100, Math.max(0, window.scrollY / length * 100)) : 0);
    };
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    window.addEventListener("hashchange", update);
    update();
    return () => { window.removeEventListener("scroll", update); window.removeEventListener("resize", update); window.removeEventListener("hashchange", update); };
  }, []);
  useEffect(() => {
    if (!open) return;
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [open]);
  return <header className="topbar">
    <nav className="nav shell" aria-label="Research chapters">
      <a className="brand" href="#overview"><span className="qfi-mark" aria-hidden="true">↗</span> QFI<span className="brand-divider"> / RESEARCH</span></a>
      <div className="chapter-links">{chapters.map(chapter => <a key={chapter.id} href={`#${chapter.id}`} aria-current={chapter.sections.some(([id]) => id === active) ? "location" : undefined}>{chapter.title}</a>)}</div>
      <button className="text-button contents-button" type="button" aria-expanded={open} aria-controls="research-contents" onClick={() => setOpen(!open)}>Contents {open ? "−" : "+"}</button>
      <button className="text-button share-button" type="button" onClick={share}>Share view ↗</button>
      <label className="mobile-nav"><span className="sr-only">Explore</span><select aria-label="Jump to research section" value={sections.some(([id]) => id === active) ? active : "overview"} onChange={event => { window.location.hash = event.target.value; setOpen(false); }}>{chapters.map(chapter => <optgroup label={chapter.title} key={chapter.id}>{chapter.sections.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</optgroup>)}</select></label>
    </nav>
    {open && <div className="contents-panel shell" id="research-contents">{chapters.map(chapter => <div key={chapter.id}><span className="mini-label">{chapter.title}</span>{chapter.sections.map(([id, label]) => <a key={id} href={`#${id}`} onClick={() => setOpen(false)} aria-current={id === active ? "location" : undefined}>{label}</a>)}</div>)}</div>}
    <div className="reading-progress" aria-hidden="true"><i style={{ width: `${progress}%` }} /></div>
    <span className="share-notice" role="status">{shareStatus}</span>
  </header>;
}

export function HeroVisual() {
  const { data } = useResearch();
  const point = data.yieldCurve.latest;
  const values = [point.two_year, point.five_year, point.ten_year];
  const validValues = values.filter((v): v is number => v != null);
  const low = Math.min(...validValues) - .2;
  const high = Math.max(...validValues) + .2;
  const coords = values.map((value, i) => [50 + i * 140, value == null ? 135 : 230 - (value - low) / (high - low) * 170]);
  return <aside className="hero-visual" aria-label="Latest saved Treasury curve and target allocation">
    <div className="visual-top"><span className="mini-label">The rate landscape</span><span className="snapshot-pill">Historical snapshot</span></div>
    <div className="curve-figure"><svg viewBox="0 0 380 280" role="img" aria-label={`Treasury par yields on ${fmtDate(point.date)}: 2Y ${values[0]}%, 5Y ${values[1]}%, 10Y ${values[2]}%`}>
      {[60, 110, 160, 210].map(y => <path key={y} d={`M30 ${y} H350`} stroke="#cad8e6" strokeDasharray="3 6" />)}
      <path className="hero-curve-line" d={coords.map(([x, y], i) => `${i ? "L" : "M"}${x} ${y}`).join(" ")} fill="none" stroke="#1768e5" strokeWidth="3" />
      {coords.map(([x, y], i) => <g key={i}><circle cx={x} cy={y} r="5" fill="#1768e5" /><text x={x} y={y - 18} textAnchor="middle" fill="#15315a" fontSize="14">{values[i]?.toFixed(2) ?? "—"}%</text><text x={x} y="267" textAnchor="middle" fill="#61728a" fontSize="12">{["2Y", "5Y", "10Y"][i]}</text></g>)}
    </svg></div>
    <div className="visual-caption"><strong>U.S. Treasury par yields</strong><span>{fmtDate(point.date)} · 3 published maturities</span></div>
    <div className="hero-allocation"><span className="mini-label">Latest saved model target</span><div className="allocation-ribbon" aria-hidden="true">{ASSETS.map(a => <i key={a} style={{ width: `${(data.researcherView.latest_signal.target_weights[a] ?? 0) * 100}%`, background: ASSET_COLORS[a] }} />)}</div><div className="asset-legend">{ASSETS.map(a => <span key={a}><i style={{ background: ASSET_COLORS[a] }} />{a} <b>{fmtPct(data.researcherView.latest_signal.target_weights[a], 0)}</b></span>)}</div></div>
    <a href="#curve" className="visual-link">Explore the curve <span>↗</span></a>
  </aside>;
}

export function ResearchOverview() {
  const { data } = useResearch();
  return <section className="section quick-overview" id="at-a-glance"><div className="shell">
    <div className="overview-title"><span className="section-index">Start here</span><h2>The research,<br />in 30 seconds.</h2><p className="section-copy">One transparent model. A complete historical record. Both the evidence and its limits.</p></div>
    <div className="overview-cards">
      <article><span className="mini-label">01 / The question</span><h3>Can exposure adapt?</h3><p>Use {data.meta.momentum_window_days}-day momentum for eligibility and {data.meta.volatility_window_days}-day volatility for sizing across Treasury ETFs.</p><a href="#signal">Understand the strategy ↗</a></article>
      <article><span className="mini-label">02 / The evidence</span><h3>A different risk path.</h3><p>Historical maximum drawdown: <strong>{fmtPct(data.summary.strategy_net.max_drawdown)}</strong> for the strategy versus <strong>{fmtPct(data.summary.benchmark.max_drawdown)}</strong> for AGG.</p><a href="#decision">Explore the historical record ↗</a></article>
      <article><span className="mini-label">03 / The trade-off</span><h3>Less risk, less return.</h3><p>Full-history CAGR: <strong>{fmtPct(data.summary.strategy_net.annualized_return)}</strong> versus <strong>{fmtPct(data.summary.benchmark.annualized_return)}</strong>. Historical results do not establish future superiority.</p><a href="#method">Inspect the methodology ↗</a></article>
    </div>
  </div></section>;
}

export function ChartFrame({ title, children, className = "chart-frame", dateSelection = true }: { title: string; children: React.ReactNode; className?: string; dateSelection?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (expanded && !dialog.current?.open) dialog.current?.showModal(); }, [expanded]);
  return <div className="chart-shell">
    <div className="chart-actions"><span className="mini-label">{dateSelection ? "Hover or tap to inspect · click to select a date" : "Hover or tap to inspect saved observations"}</span><button type="button" className="text-button" onClick={() => setExpanded(true)} aria-label={`Expand ${title}`}>Expand ↗</button></div>
    <div className={className} role="group" aria-label={title}>{children}</div>
    {expanded && <dialog ref={dialog} className="chart-dialog" aria-label={title} onClose={() => setExpanded(false)} onClick={event => { if (event.target === event.currentTarget) dialog.current?.close(); }}><div className="dialog-heading"><h3>{title}</h3><button className="text-button" type="button" onClick={() => dialog.current?.close()} autoFocus>Close ×</button></div><div className="expanded-chart">{children}</div><p className="research-caption">Saved historical observations. Escape closes this view.</p></dialog>}
  </div>;
}

export function RevealSections() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add("is-revealed"); observer.unobserve(entry.target); }
    }), { threshold: .04 });
    document.querySelectorAll(".section-head,.overview-cards,.research-subhead").forEach(node => {
      // Only prepare off-screen content; everything stays visible without JS.
      if (node.getBoundingClientRect().top > window.innerHeight) { node.classList.add("reveal-ready"); observer.observe(node); }
    });
    return () => { observer.disconnect(); document.querySelectorAll(".reveal-ready").forEach(node => node.classList.remove("reveal-ready")); };
  }, []);
  return null;
}

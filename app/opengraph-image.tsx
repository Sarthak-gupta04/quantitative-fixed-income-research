import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { MetaData, YieldCurveData } from "@/types/data";

export const alt = "Fixed-Income Strategy & Risk Research — Sarthak Gupta. Interactive historical Treasury allocation research.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const [metaText, curveText] = await Promise.all([
    readFile(join(process.cwd(), "public/data/meta.json"), "utf8"),
    readFile(join(process.cwd(), "public/data/yield_curve.json"), "utf8"),
  ]);
  const meta: MetaData = JSON.parse(metaText);
  const curve: YieldCurveData = JSON.parse(curveText);
  const yields = [curve.latest.two_year ?? 0, curve.latest.five_year ?? 0, curve.latest.ten_year ?? 0];
  const low = Math.min(...yields) - .2;
  const high = Math.max(...yields) + .2;
  const points = yields.map((y, i) => `${30 + i * 120},${230 - (y - low) / (high - low) * 150}`).join(" ");
  return new ImageResponse(<div style={{ width: "100%", height: "100%", display: "flex", background: "#f7f6f2", color: "#17191c", padding: "64px", flexDirection: "column" }}>
    <div style={{ display: "flex", color: "#1768e5", fontSize: 18, letterSpacing: 3 }}>QFI / INDEPENDENT QUANTITATIVE RESEARCH</div>
    <div style={{ display: "flex", flex: 1, alignItems: "center", gap: 48 }}><div style={{ display: "flex", width: 700, flexDirection: "column", fontSize: 72, lineHeight: 1.02, letterSpacing: -4 }}><span>Fixed-Income</span><span>Strategy &amp;</span><span style={{ color: "#1768e5" }}>Risk Research.</span></div><div style={{ display: "flex", width: 290, flexDirection: "column" }}><svg width="290" height="280" viewBox="0 0 290 280"><path d="M20 80H280M20 155H280M20 230H280" stroke="#ced9e7" /><polyline points={points} fill="none" stroke="#1768e5" strokeWidth="4" /></svg><span style={{ display: "flex", fontSize: 16, color: "#61728a" }}>Treasury par yields · {curve.latest.date}</span></div></div>
    <div style={{ display: "flex", borderTop: "1px solid #dddcd6", paddingTop: 24, justifyContent: "space-between", fontSize: 20, color: "#526075" }}><span>Sarthak Gupta</span><span>{meta.start_date.slice(0, 4)}–{meta.end_date.slice(0, 4)} · Historical research, not live advice</span></div>
  </div>, size);
}

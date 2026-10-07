"use client";

export default function ResearchError({ reset }: { reset: () => void }) {
  return <main className="shell" style={{ padding: "100px 0" }}><span className="eyebrow">QFI / Research</span><h1>The research view couldn’t load.</h1><p>Try loading the saved snapshot again. No research calculations or data have been changed.</p><button className="outline-button" type="button" onClick={reset}>Try again</button></main>;
}

"use client";

import React from "react";
import type { ReferencesData } from "@/types/data";

export default function References({ data }: { data: ReferencesData }) {
  const groups = data.references.reduce<Record<string, typeof data.references>>((result, reference) => {
    (result[reference.category] ??= []).push(reference);
    return result;
  }, {});
  return (
    <section id="references" className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-8"><div className="mb-2 flex items-center gap-2"><span className="text-xs font-semibold uppercase tracking-widest text-blue-400">13</span><span className="text-xs uppercase tracking-widest text-slate-500">References</span></div><h2 className="text-2xl font-semibold text-slate-100">Sources & Documentation</h2><p className="mt-2 text-sm text-slate-400">Links are supplied directly by the generated research metadata.</p></div>
      <div className="grid gap-5 md:grid-cols-2">
        {Object.entries(groups).map(([category, references]) => <div key={category} className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-5"><h3 className="text-sm font-semibold text-slate-200">{category}</h3><ul className="mt-4 space-y-4">{references.map((reference) => <li key={reference.id}><a href={reference.url} target="_blank" rel="noreferrer" className="text-sm font-medium text-blue-300 hover:text-blue-200 hover:underline">{reference.title}</a><p className="mt-1 text-xs text-slate-500">{reference.publisher} · {reference.use}</p></li>)}</ul></div>)}
      </div>
    </section>
  );
}

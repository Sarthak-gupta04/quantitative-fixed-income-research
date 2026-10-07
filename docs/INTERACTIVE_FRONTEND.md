# Interactive frontend handoff

Implemented on `codex/interactive-research` in an isolated worktree based on
merged `origin/main` commit `3f718e2a5442a38771237836526db95c3de9ed27`.
The existing main checkout was not updated or modified.

## What changed

- Saved Treasury-curve hero, concise research overview and chapter navigation.
- Shared historical date and episode focus across NAV, risk and allocation views.
- All 273 observable rebalances are inspectable and replayable. The 208 saved
  material-change diagnostics remain distinguished from other rebalances.
- Separate signal, effective-holdings, NAV and risk observation dates.
- Clickable linked charts, expandable native dialogs, a saved-return heatmap,
  saved maturity comparisons, configuration comparison and discrete rate shocks.
- Shareable URL selections, searchable glossary, saved provenance links,
  printable standalone HTML brief and generated social preview image.
- Responsive controls, keyboard actions, native dialog focus/Escape handling,
  existing reduced-motion support and UTC date display.

Selections read existing JSON. They do not rerun the engine, optimize parameters,
rebase period charts or change headline statistics. Rate shocks select only the
five saved scenarios for either of the two saved allocations. Configuration
comparison explicitly identifies its common evaluation window. Optional new
financial analyses are not part of this frontend change.

## Validation (2026-10-07)

Passed:

```text
npm exec tsc -- --noEmit --incremental false
npm run build
node scripts/verify-research-ui.cjs
git diff --check
```

The read-only verification script checks chronological lookups, pinned chart
samples, saved rebalance/diagnostic consistency, URL restoration and invalid
inputs, and protected tracked files. It is not a replacement for analytics tests.
Python tests and expensive research generation were not rerun.

Browser checks covered desktop and 390px mobile layout, shared URL restoration,
date submission, rebalance stepping/replay, chart click-to-select and expansion,
episode selection, curve comparison, configuration selection, keyboard shock
selection, heatmap selection, glossary search and copied view links. All 19 main
sections rendered without page-wide horizontal overflow. Two development warnings
(chart highlight rendering and Next.js smooth-scroll annotation) were corrected.
No runtime errors were observed in the final local production checks.

Production HTTP checks returned 200 for `/`, `/research-brief`, the HTML download
and `/opengraph-image`. The brief has three sections and an attachment header for
download. Print-to-PDF is browser-provided; no pre-generated PDF is included.
Build tracing includes the saved data files needed by the brief route.

## Existing tooling limitations

`npm ci` could not validate the existing lockfile: optional `@emnapi/core` and
`@emnapi/runtime` entries were missing. The same failure occurred with
`--legacy-peer-deps`. Validation used the already-installed dependency tree from
the previous validated test checkout. No package manifest or lockfile was edited
and no new dependencies were added. A fresh clean dependency installation remains
unverified and should be addressed separately before a release.

ESLint could not run because the existing repository has no ESLint flat config.
No unrelated lint migration was performed. React best-practice review focused on
stable hook dependencies, derived state, accessibility and saved-data integrity.

## Preview and release boundary

```text
npm run dev -- --hostname 127.0.0.1 --port 3010
# or, after building:
npm run start -- --hostname 127.0.0.1 --port 3011
```

`analytics/`, `tests/`, `public/data/`, `package.json`, `package-lock.json` and
the generated Next.js typing entrypoint remain unchanged. The initial validation
handoff did not commit, push, merge or deploy. Release through a reviewed pull
request targeting `main`; verify a successful remote build before merging.

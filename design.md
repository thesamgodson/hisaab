# Design — Hisaab

A locked, human-first design system for Hisaab. Public-service tasks outrank
data display: every surface should answer what affects the person, what they
are owed, what to do next, who is accountable, and where the evidence came
from.

## Genre

Civic editorial: the trust and restraint of a public record, with the speed
and clarity of a modern service interface.

## Macrostructure family

- Marketing page: Narrative Workflow. PIN entry is the first real action;
  the map is a secondary district-browsing tool.
- App pages: Workbench with an index-first summary. Next action first,
  representatives second, complaint path third, raw evidence last.
- Content pages: Long Document if one is ever required. Do not add a page when
  progressive disclosure on an existing page will do.

## Theme

Almanac, adapted for public service:

- `--color-paper`: `oklch(0.975 0.012 85)`
- `--color-paper-2`: `oklch(0.95 0.016 85)`
- `--color-surface`: `oklch(0.99 0.008 85)`
- `--color-ink`: `oklch(0.22 0.025 255)`
- `--color-ink-2`: `oklch(0.41 0.025 255)`
- `--color-muted`: `oklch(0.46 0.02 255)`
- `--color-rule`: `oklch(0.84 0.018 85)`
- `--color-accent`: `oklch(0.43 0.15 276)`
- `--color-focus`: `oklch(0.52 0.17 276)`

Status colours are evidence annotations, never the brand: green means a
higher reported rate, amber a middle reported rate, and red a lower reported
rate or a flagged shortfall. Text always states the exact value or caveat.

## Typography

- Display and wordmark: Newsreader, weight 600
- Body and controls: Geist, weights 400 and 600
- Figures and PINs: Geist Mono, weight 500
- Display tracking: `-0.025em`
- Body floor: `1rem`; labels never below `0.6875rem`

Fonts load through `next/font` so they are self-hosted and reserve their
metrics before paint.

## Spacing

A four-point named scale lives in `web/src/app/tokens.css`. Page components
use system classes and semantic tokens rather than one-off colour values.

## Motion

- No scroll-triggered reveal sequence.
- State changes use `--dur-short: 160ms` and `--ease-out`.
- Focus indicators are immediate and never animated.
- Reduced motion removes all non-essential animation.

## Microinteractions stance

- No decorative hover lifts, glass effects, gradient text, or emoji icons.
- Disclosures are native `<details>` elements with 48px minimum summaries.
- Loading regions reserve space so hydration and geolocation do not shift the
  page.
- Success is quiet; limitations are stated in plain language.

## CTA voice

- Primary: solid civic indigo, short verb-led label, 10px radius.
- Secondary: paper surface with a hairline rule.
- Links and buttons never wrap.

## Per-page allowances

- Home may use the existing district map, after the PIN task.
- Brief pages use no decorative enrichment; the person’s next step is the
  visual anchor.
- Evidence is always present but progressively disclosed.

## What every page shares

- Newsreader wordmark and headings, Geist controls, Geist Mono figures.
- Warm paper, deep ink, civic indigo used sparingly.
- A compact edge-aligned masthead and one-line colophon footer.
- Plain-language need first, scheme acronym second.
- One `<main>`, no horizontal scroll, and verified layouts at 320, 375, 414,
  and 768 CSS pixels.

## What pages may differ on

- Home uses a two-column task-first opening above a secondary map.
- PIN and district briefs share the same workbench hierarchy, but the PIN
  brief names exact representatives while the district brief stays plural.

# Design — Hisaab

Hisaab is one public-service interface, not a landing page followed by two
different products. The design exists to help a person identify their area,
understand one problem, and take one defensible next step.

## Genre

Modern-minimal civic utility. It should feel calm, specific, and operational —
closer to a well-made public service than a campaign site or analytics dashboard.

## Macrostructure family

- Canonical app surface: Index-First. The area lookup is the index; a result
  replaces it in the same route and preserves a clear way back.
- Result mode: one continuous task document — context, data caveat, complaint
  guide, accountable people, evidence.
- Compatibility routes: redirects only. They never own a second visual product.

## Theme

- White paper and cool graphite text.
- One civic blue for actions and links.
- Red, amber, and green appear only when the underlying data carries that state.
- No gradients, glass, decorative shadows, illustration, or ornamental colour.

All values live in `web/src/app/tokens.css`; component CSS uses tokens only.

## Typography

- UI and display: Aptos where available, then metric-stable Geist and Segoe UI.
- Wordmark and figures: Geist Mono.
- Body: 16px minimum, 1.55 line-height.
- Headings: 700; body: 400. No serif display type and no giant headline.
- Five sizes maximum. Numeric evidence uses tabular figures.

## Spacing and shape

- Four-point spacing scale.
- Content measure: 48rem for results, 36rem for lookup.
- Radius: 4–8px. A control may be rounded; whole sections are not floating cards.
- Structure comes from whitespace and rules, not repeated containers.

## Motion

- No entrance, scroll, stagger, lift, shimmer sweep, or decorative motion.
- Hover and active feedback use colour only, at 120ms.
- Focus rings are immediate. Reduced motion removes remaining transitions.

## Interaction

- One primary action at a time.
- PIN submission is explicit; the sixth digit never navigates by surprise.
- District browsing is a secondary disclosure and loads only when requested.
- Complaint kits use one native select and show one guide at a time.
- The first local grievance rung is visible; escalation and raw evidence disclose.
- Every claim remains paired with its official source or an explicit scope caveat.

## Voice

- Plain problem language before scheme names.
- Short labels: “Check this PIN”, “Open official route”, “Search another area”.
- Never call missing data an all-clear.
- Never present a district aggregate as a decision about an individual case.

## Responsive contract

- Mobile-first at 320, 375, 414, and 768 CSS pixels.
- No horizontal scrolling or two-line button labels.
- One column until the content can support two without compression.
- `html` and `body` use `overflow-x: clip`.

## Exports

The canonical CSS export is `web/src/app/tokens.css`. The equivalent mappings are:

- Tailwind: paper → `background`, ink → `foreground`, accent → `primary`.
- DTCG: `color.paper`, `color.ink`, `color.accent`, `space.*`, `font.ui`.
- shadcn/ui: `--background`, `--foreground`, `--primary`, `--border`, `--ring`.

Those exports must mirror `tokens.css`; they do not define independent values.

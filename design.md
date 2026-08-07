# Design — Hisaab

Hisaab is a public welfare account. It helps a person ask a simple civic
question—**where did the money go?**—without turning incompatible government
datasets into a score, verdict, or false grand total.

The account is the product. Complaint guidance and representatives are useful
actions around the account; they are not the product's organizing idea.

## Product promise

**Enter an area. Read the exact public record. See what is missing. Know where
to question it.**

Hisaab does not decide eligibility, prove wrongdoing, predict complaint
success, file a grievance, or claim to be a government service.

## Genre

Modern-minimal civic ledger: calm, exact, and legible under stress. The visual
reference is a carefully edited public account or audit sheet, not a SaaS
dashboard, campaign site, government imitation, or AI assistant.

## App macrostructure

- Entry: a guided three-step ledger path with one prominent PIN task. State,
  district, and location remain secondary ways to identify the same area.
- Account: a bounded area masthead, a full-width service index, exact evidence
  inside the selected row, state-only context, coverage gaps, contextual rights
  and routes, then representatives.
- Compatibility URLs restore the same account with an action section expanded;
  they do not create a separate visual product.
- No persona modes, dashboard tabs, mandatory issue diagnosis, or map-first path.

## Information order

1. **Area.** PIN or a state-scoped district.
2. **Public account.** Scheme-specific money, delivery, or process facts.
3. **Provenance.** Metric meaning, period, geographic grain, source, retrieval
   date, and claim-register ID travel with every record.
4. **Coverage limits.** State-only, unpublished, frozen, estimated, or missing
   data is named plainly; absence is never rendered as zero activity.
5. **Question it.** The person chooses a scheme or service. Data never chooses
   the complaint for them.
6. **Rights and official routes.** Sourced entitlements, all verified routes,
   preparation, CAPTCHA handoff, print, and share.
7. **Representatives.** Plural district-overlap MPs as optional oversight
   context, never the grievance authority.

## Evidence contract

- Never normalize different schemes into generic allocated, released, spent,
  or utilization labels unless the source uses that exact stage.
- Never add incompatible money stages, periods, or geographic grains.
- District records and state context are visually separate.
- Reporting period and retrieval date are different concepts and stay labelled.
- A daily snapshot is not a coverage rate. A project value is not a release. A
  receipt is not expenditure. An estimate is not spend.
- An area aggregate does not determine a person's eligibility or prove an
  individual complaint.
- Use `Not published`, `Not retained`, or `No district-grain record found`, not
  `0`, when the source or pipeline is silent.

## Visual system

- Warm paper, deep navy text, quiet warm-grey rules, and one civic blue for
  navigation, focus, and action.
- Red, amber, and green appear only when a sourced record carries that state,
  never as decorative status colour.
- The account uses a guided ledger rhythm: an editorial masthead, full-width
  service rows, explicit money/delivery/process labels, exact fact panels, and
  numbered action steps. No dashboard mosaic.
- One reading column on mobile; a two-column record grid only when space permits.
- The primary form submit is the only strongly filled control in a section.
- Corners are 4–8px. Bounded panels use borders and paper contrast; shadows are
  reserved for overlays and the account has none.
- All implementation values live in `web/src/app/tokens.css`.

## Typography

- Display: Noto Serif for the English editorial hierarchy, with the matching
  Noto Serif family required when additional scripts ship.
- Body: Aptos when installed, then Noto Sans for the web and each fully
  supported Indic script. Aptos is never the multilingual foundation.
- Body text is at least 16px with 1.55 line height and remains readable at 200%.
- Headings are sentence case, compact, and never decorative giant type.
- Numeric evidence uses tabular figures. Monospace is reserved for claim IDs.

## Interaction

- Native semantic controls, persistent labels, explicit submit, and 44px targets.
- The sixth PIN digit never navigates by surprise.
- Server-rendered HTML owns the useful result. Client JavaScript enhances
  district browsing, location matching, copy, share, and disclosures.
- Public non-personal URL state survives refresh and sharing. Names, Aadhaar,
  phone numbers, grievance text, documents, and coordinates never enter a URL.
- Motion is limited to necessary state feedback. No entrance, scroll, stagger,
  shimmer, lift, parallax, or decorative animation.
- Hover and open states may change paper tone, but never colour-code service
  performance or imply that one scheme matters more than another.

## Adaptive assistance

The interface adapts to the task, not to a guessed persona. Every person gets
the same account: human service names first, exact records on request, and
official action only when they choose it.

- Deterministic navigation, disclosures, and reviewed plain language come
  first. The complete account works without AI, client JavaScript, or an account.
- AI may suggest existing scheme or service IDs from a short search phrase only
  after deterministic matching fails. The person confirms every suggestion.
- AI never writes evidence, selects a headline metric, combines figures, ranks
  districts or routes, infers eligibility or wrongdoing, or chooses a complaint.
- Runtime natural-language-to-SQL is not a citizen feature. A model never
  receives database access, personal identifiers, complaint text, documents,
  coordinates, or provider credentials from a person using Hisaab.
- Translations are drafted offline, reviewed by a person, versioned by stable
  semantic ID, and published with numbers, units, dates, places, sources, and
  claim IDs unchanged. Missing translation falls back to the exact English record.
- Any future simplified explanation is bound to one structured evidence record,
  names what the record does not prove, cites that record, and fails back to the
  exact source-bound text when validation fails.
- AI is quiet infrastructure, never a chatbot, persona, badge, or substitute for
  the public record.

## Complaint layer

- Complaint coverage is independent of local performance-data coverage.
- The person chooses the issue; no score, percentage, or missing record selects it.
- All verified route rungs remain available with equal visual weight unless an
  audited ordering field is added.
- Legal entitlement source and complaint-destination source remain distinct.
- Hisaab never submits a complaint or automates a CAPTCHA. Personal details are
  entered only on the official service by the person using it.

## Assisted and offline use

- The core account and action plan work without an account, upload, or continuous
  connection.
- A helper can use Hisaab without entering personal case data.
- Print uses a plain A4 account/action sheet and excludes navigation.
- Share restores public area and guidance only; it never creates a case record.

## Anti-slop rules

- No marketing hero, impact theatre, vanity statistics, testimonial, carousel,
  chat bubble, chatbot persona, or “AI-powered” framing.
- No gradient, glass, glow, decorative blob, arbitrary illustration, floating
  card mosaic, excessive pills, icon-only action, or fake government chrome.
- No map as the first task, score as a verdict, grand total across schemes, or
  complaint as the first screen.
- Function carries the interface. Enrichment and decorative imagery are off.

## Tenet gates

1. **Sourced claims:** claim, source, period, geographic scope, and retrieval
   date travel together.
2. **No misleading claims:** labels, comparisons, order, and visual emphasis do
   not outrun the source.
3. **No CAPTCHA automation:** official human verification is handed off intact.
4. **No lossy refresh:** geographic grain, coverage, detail, and money never
   regress.

The first two gates apply to interface composition as much as database values.
A true number can still mislead when renamed, ranked, totalled, colour-coded, or
placed beside the wrong action.

## Responsive and performance contract

- Verify at 320, 375, 414, and 768 CSS pixels and at 200% zoom.
- No horizontal page scroll. Long district names, sources, and claim IDs wrap.
- Core lookup and account output remain useful with server-rendered HTML and on
  slow, intermittent mobile connections.
- Progressive enhancement never owns the only route to the public account or
  complaint guidance.
- Closed screen disclosures open fully in print, so compact browsing never
  removes evidence from an A4 account or action sheet.

## Canonical export

`web/src/app/tokens.css` is the implementation source of truth. Other token
formats may mirror it but never define independent values.

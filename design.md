# Design — Hisaab

> Status: proposed service direction for the next tested prototype. Production
> partially conforms, but the issue-first flow must be validated with citizens
> before it replaces the current interface.

Hisaab is an independent public-service casework utility. Its job is not to
display a district dashboard. Its job is to help a person whose welfare benefit
is delayed, denied, or unclear complete the next accountable action without
having to understand scheme acronyms, government structure, or district data.

## Service promise

**Tell us what happened. Leave with one defensible next step, what to prepare,
and what to do if it does not work.**

Hisaab does not decide eligibility, predict grievance success, file a complaint,
collect case details, or claim to be a government service.

## Genre

Public-service casework utility: calm, literal, and operational. The visual
reference is a well-edited action sheet or field guide, not a SaaS dashboard,
campaign site, government imitation, or AI assistant.

## Service shape

- One service shell with staged states, not three separate products or one long
  page showing everything at once.
- Default prototype hypothesis: `problem → trigger → area → action → prepare →
  escalate`.
- One question or decision per state; a visible Back control preserves answers.
- PIN is the primary area input. State and district are an explicit fallback.
  Device location is optional and explained before use.
- Complaint rights are available independently of local performance-data
  coverage. Aggregate data never chooses a person's issue for them.
- District evidence and representatives are supporting context after the action,
  not the entry point and not a substitute for the grievance authority.
- Compatibility URLs may restore a state in the same shell; they do not own a
  second visual product.

## Information order

1. **What happened?** Human problem labels across every supported entitlement.
2. **Where?** Only the location needed to find the correct authority.
3. **Do this now.** A destination-specific verb: call, file online, check status,
   visit or write, or use the named official app.
4. **Your right.** The concise entitlement, conditions, official source, scope,
   and verification date.
5. **Prepare and keep.** Evidence to carry, a complaint script with placeholders,
   the receipt or registration number to expect, and what to retain.
6. **If unresolved.** The sourced waiting period and next verified rung.
7. **Need help?** A printable action sheet and an assisted route such as a CSC
   when the source supports it.
8. **Why this advice?** Area evidence with source, period, geography, and a clear
   warning that aggregate data does not determine an individual case.
9. **Who represents this area?** Follow-up or oversight context only, never the
   primary grievance route.

## Visual system

- White paper, near-black text, quiet grey rules, and one civic blue for actions
  and links.
- Red, amber, and green appear only when a sourced datum carries that state, and
  never without a text label.
- One narrow reading column. A wider evidence table is allowed only when the
  comparison requires it.
- Hierarchy comes from type, spacing, indentation, and rules—not nested cards.
- The primary action is the only strongly filled control in a state.
- Corners are 4–8px. Shadows are reserved for a genuinely overlaid surface.
- All values live in `web/src/app/tokens.css`; component CSS consumes tokens.

## Typography

- Primary multilingual family: Noto Sans for each fully supported script, then
  the platform's system sans.
- Aptos may be a Latin preference only. It is not the multilingual foundation;
  its published character set does not cover the Indic scripts Hisaab needs.
- Body: 16px minimum and 1.55 line height. Text remains readable at 200% zoom.
- Headings: sentence case, compact, and no heavier than needed. Five sizes
  maximum.
- Numeric evidence uses tabular figures. Monospace is reserved for identifiers,
  not the wordmark or ordinary prose.

## Interaction

- Use native semantic controls. Labels stay visible; placeholders are examples,
  not labels.
- Primary targets are at least 44×44 CSS pixels with a visible keyboard focus
  state and no hover-only meaning.
- Validate on explicit submission. Put the error beside the field and move focus
  to an error summary when several fields fail.
- The sixth PIN digit never navigates by surprise.
- Show only the information needed for the current decision. Native disclosures
  may reveal escalation, evidence, sources, or representative context.
- Preserve progress across Back, refresh, interruption, and shareable non-personal
  URLs. Never put case details in a URL.
- Motion is limited to necessary state feedback. No entrance, scroll, stagger,
  lift, shimmer, parallax, or decorative animation.

## Content and provenance

- Lead with the person's problem, then name the scheme and administrative terms.
- Use specific verbs. “Call the helpline” is acceptable; “Open official route”
  is not.
- Every legal, deadline, money, performance, and route claim carries an adjacent
  source, period or verification date, and geographic scope.
- Distinguish the source for a legal entitlement from the destination used to
  submit a grievance.
- Say `Not published` or `Not available for this area`, never `0`, when the source
  is silent.
- Never call a grievance “solved” because a portal marks it disposed.
- Never present district or state aggregates as evidence about an individual's
  eligibility, case, representative, or likelihood of success.
- A language ships only when all task-critical labels, legal claims, instructions,
  errors, and printable content are human-reviewed and synchronized with English.
  No partial machine-translated legal experience.

## Assisted and offline use

- The core result must produce a useful phone, visit, or paper plan without an
  upload, account, or continuous connection.
- A helper can use the service with a person without entering names, Aadhaar,
  phone numbers, grievance text, documents, or precise coordinates into Hisaab.
- Print uses a plain A4 action sheet with authority, script, checklist, source,
  and escalation. It excludes navigation and decorative UI.
- Share creates a non-personal route to the same public guidance, never a stored
  case record.

## Anti-slop rules

- No marketing hero, impact theatre, vanity statistics, testimonials, carousel,
  chat bubble, chatbot persona, or “AI-powered” framing.
- No gradient, glass, glow, decorative blob, arbitrary illustration, giant type,
  floating card mosaic, excessive pills, or icon-only action.
- No map as the first task, score as a verdict, or data flag as a preselected
  grievance.
- No fake government emblem, tricolour chrome, or visual claim of official status.
- No decorative novelty that makes the service less predictable under stress.

## Tenet gates

Every release must pass all four gates:

1. **Sourced claims:** claim, source, period, and scope travel together.
2. **No misleading claims:** language and visual emphasis do not outrun the data.
3. **No CAPTCHA automation:** hand off to the official human flow intact.
4. **No lossy refresh:** granularity, geographic coverage, and money never regress.

The first two gates apply to interface composition as well as database values. A
technically true number can still mislead when relabelled, ranked, colour-coded,
or placed beside the wrong action.

## Responsive and performance contract

- Design at 320, 375, 414, and 768 CSS pixels before adding wider layouts.
- No horizontal page scroll. Long names and identifiers wrap without hiding the
  primary action.
- The core route works with server-rendered HTML and remains useful on slow,
  intermittent mobile connections.
- Progressive enhancement may improve search, copy, save, and disclosures, but
  never owns the only route to the guidance.

## Canonical exports

`web/src/app/tokens.css` is the implementation source of truth. Tailwind, DTCG,
and shadcn mappings may mirror it but never define independent values.

The research rationale, service blueprint, and validation gates are recorded in
[`SERVICE_DESIGN.md`](SERVICE_DESIGN.md). The field study needed before locking
the issue-first sequence is in
[`USER_RESEARCH_PLAN.md`](USER_RESEARCH_PLAN.md).

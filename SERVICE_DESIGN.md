# Hisaab service design

## Decision

Hisaab should become a **public-service casework utility**, not a district
performance dashboard. Its primary job is:

> When a promised welfare benefit is delayed, denied, or unclear, help me
> complete the next accountable action—on my phone or with a helper—without
> exposing personal data.

This is the recommended prototype direction, not a claim that citizen discovery
is complete. Desk research and a repository journey audit are complete. Direct
observation with beneficiaries, helpers, and frontline intermediaries is still
required before the issue-first flow is treated as final.

## Why this direction

- The repo's rare capability is not another district score. It is the combination
  of source-backed entitlements and verified grievance rungs.
- Public-service guidance says user needs should come from observed users, not
  stakeholder assumptions, and discovery should include the whole journey,
  disabled people, and people with low digital confidence
  ([GOV.UK user needs](https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs),
  [discovery research](https://www.gov.uk/service-manual/user-research/user-research-in-discovery)).
- India's GIGW 3.0 calls for citizen-centred, simple, accessible, mobile-ready,
  multilingual government information; UX4G adds practical patterns for visible
  labels, validation, keyboard use, and minimum touch targets
  ([GIGW](https://guidelines.india.gov.in/),
  [UX4G foundations](https://www.ux4g.gov.in/foundations?lang=en),
  [UX4G input](https://www.ux4g.gov.in/components/input)).
- Mobile is the dominant connected channel, but capability is unequal. MoSPI's
  2025 telecom survey reports that 98.8% of connected households used a mobile
  network, while rural gaps persisted in individual device ownership and basic
  attachment tasks. The implication is mobile-first, not mobile-only: provide
  helper, print, phone, and visit routes without requiring uploads
  ([MoSPI press release](https://www.mospi.gov.in/sites/default/files/press_release/Final_press%20release_CMS_T.pdf),
  [full report](https://mospi.gov.in/sites/default/files/publication_reports/CMST_report_m.pdf)).
- A Delhi cash-transfer experiment found information alone was not enough for
  many eligible women, while application assistance increased applications.
  This is one programme in one city, so it is a design hypothesis—not a national
  effect estimate—but it supports testing guided completion over information
  display ([AEA study](https://www.aeaweb.org/articles?id=10.1257/pol.20240212)).
- CPGRAMS itself is a multi-channel service: online filing is free, plain paper
  and post are allowed, CSC assistance is available, and a registration ID is
  used for tracking. Hisaab should prepare people for these official channels,
  not try to replace or automate them
  ([CPGRAMS](https://www.pgportal.gov.in/),
  [CPGRAMS FAQ](https://www.pgportal.gov.in/Home/Faq)).

These are standards and design inputs, not evidence that Hisaab is government-
approved, GIGW-certified, or UX4G-certified. UX4G explicitly disclaims implied
government endorsement from use of its materials
([UX4G disclaimer](https://www.ux4g.gov.in/disclaimer)).

## Double Diamond

The [Design Council Double Diamond](https://www.designcouncil.org.uk/resources/framework-for-innovation/)
separates divergent and convergent work across Discover, Define, Develop, and
Deliver. Hisaab's current position is the end of desk discovery, before field
validation.

### Discover

Completed:

- Audited the current one-page journey, route data, evidence display, and scheme
  coverage.
- Reviewed Indian public-service standards, accessibility guidance, connectivity
  evidence, grievance mechanisms, typography coverage, and service-design
  practice.
- Identified the product's distinctive asset: legal entitlement plus an ordered,
  verified grievance route.

Still required:

- Observe people using Hisaab for a real or carefully redacted welfare problem.
- Include direct beneficiaries, family helpers, CSO caseworkers, CSC/VLE or
  frontline helpers, older people, disabled people, and low-confidence users.
- Follow the journey beyond the webpage: phone, portal, paper, office, receipt,
  waiting, status check, and escalation.
- Test multiple states and languages rather than treating an English prototype
  as nationally representative.

### Define

Problem statement:

> A person facing a delayed, denied, or unclear welfare benefit needs to identify
> the correct first grievance action and prepare what to say or carry, without
> understanding scheme acronyms, government structure, or district statistics.

Required outcomes:

- Identify the correct official next channel.
- Understand the relevant promise or entitlement and its conditions.
- Know what to prepare, what receipt to expect, and what to keep.
- Know when and how to recover if the first action fails.
- Understand that Hisaab is independent and that area data does not decide a
  personal case.

Non-goals:

- Determining eligibility or predicting success.
- Filing a complaint or completing a CAPTCHA.
- Collecting grievance text, documents, Aadhaar, names, phone numbers, or precise
  location.
- Ranking people or areas as advice.
- Becoming a scheme catalogue, news site, or impact-marketing page.

### Develop

Three flows should be task-tested:

| Concept | Strength | Main risk | Disposition |
| --- | --- | --- | --- |
| Issue-first companion | Matches the person's immediate problem | Issue vocabulary may not match local speech | Recommended hypothesis |
| Scheme-assisted flow | Useful when the person knows the scheme | Acronyms and scheme boundaries exclude people | Test as an alternate path |
| Location-first flow | Quickly scopes authorities and evidence | Encourages browsing before action | Control, not default |

Three visual treatments should use the same content:

- **Action brief:** the next action is dominant, with right and escalation below.
- **Field guide:** concise numbered instructions suited to helpers and print.
- **Plain service form:** one question per state with a final action summary.

Do not run an aesthetic preference poll. Test whether a person can identify the
problem, select the correct route, understand the reason, recover from a wrong
choice, and carry the plan into the official channel.

### Deliver

Ship content order before decoration. Release one supported journey at a time
behind the same shell, while preserving all existing claim and data gates.

Measure:

- Correct first-route selection.
- Comprehension of the entitlement and Hisaab's independent status.
- Unaided completion of a call, copy, print, or visit plan.
- Recovery from a wrong issue or area.
- Successful transition to the official channel.
- Ability to resume, share a non-personal route, or use the result with a helper.
- Keyboard, screen-reader, large-text, low-connectivity, and print success.

Do not use time-on-page, card clicks, scroll depth, or raw engagement as impact.
An early prototype may test whether people can find the first authority within
60 seconds and prepare a usable plan within three minutes, but these are research
targets, not published performance claims.

## Service blueprint

| Stage | Person sees | Person does | Hisaab responsibility | Official/offline handoff |
| --- | --- | --- | --- | --- |
| Problem | Human descriptions, not scheme acronyms | Chooses what happened | Offer all supported rights; never data-gate | None |
| Trigger | Concrete events and conditions | Confirms the closest situation | Avoid implying eligibility | None |
| Area | PIN, then state/district fallback | Provides only public area context | Explain location use; store no precise location | Postal/district resolution |
| First action | Named authority, verb, prerequisites | Calls, files, checks, visits, or writes | Cite and verify the route; no CAPTCHA automation | Official helpline, portal, app, or office |
| Prepare | Script, evidence checklist, expected receipt | Copies, prints, or notes | Use placeholders; collect no personal fields | Phone note, paper, helper, CSC |
| Wait | Sourced timeframe and keep-list | Retains receipt and date | Distinguish submitted, disposed, and resolved | Official status channel |
| Escalate | Next verified rung and condition | Escalates when appropriate | Preserve ordered rungs and route scope | Appellate or grievance authority |
| Context | Area evidence and representatives | Uses evidence for follow-up | Show source, period, scope, caveat | Representative only after procedure |

The service must join online and offline channels rather than assume the website
is the whole service
([whole-problem mapping](https://www.gov.uk/service-manual/design/map-a-users-whole-problem),
[joined channels](https://www.gov.uk/service-manual/service-standard/point-3-join-up-across-channels),
[assisted digital](https://www.gov.uk/service-manual/assisted-digital/)).

## Required service states

1. `problem`
2. `trigger`
3. `area`
4. `action`
5. `prepare`
6. `waiting`
7. `escalate`
8. `evidence` (secondary)
9. `representatives` (secondary)

One-question pages are a useful interaction model even when implemented as
staged states in one shell: ask only what is needed, preserve a visible Back
path, and retain answers
([GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/)).

## Mobile reference composition

This is content order, not final copy or an invented grievance route. Braces mark
source-backed values supplied by the route registry.

```text
Hisaab                                    Independent — not a government website

What happened?
Choose the closest problem. You can change this later.

( ) Wages or payment are late
( ) Ration was refused or missing
( ) Pension has not arrived
( ) Housing instalment is delayed
( ) A school right was denied
( ) Something else we cover

[Continue]
```

```text
Back                                               Hisaab

Do this now
{Specific verb} {named first authority}
{Phone, official URL, app, or office instruction}

[Primary action with destination]

Before you start
{Minimal sourced prerequisites}

Keep
{Expected receipt, registration number, date, or paper copy}

Your right
{Concise entitlement and conditions}
Source: {official title} · {period/scope}

[Prepare what to say]  [Print this plan]

If this does not work
{Sourced wait condition} → {next verified rung}

Why this advice?                         collapsed
Area evidence                            collapsed
Representatives                          collapsed
```

The primary action names its consequence: `Call {authority}`, `File on
{portal}`, `Check status`, or `Prepare a written complaint`. It never says
`Continue`, `Learn more`, or `Open official route` when a more specific verb is
known.

## Data and content changes required before implementation

### Decouple rights from performance data

The complaint issue list must come from the entitlement and route registry, not
from schemes present in local `money_flow` or score data. RTE is the decisive
test: a state-grain UDISE+ dataset cannot be allowed to hide a valid education
complaint route.

### Make route semantics explicit

Each grievance rung needs, where its official evidence supports them:

- `action_type`: `call`, `file_online`, `check_status`, `visit_write`, or
  `app_only`
- destination label and responsible authority
- route URL or phone number
- prerequisites
- expected receipt or registration proof
- response or wait period with scope
- escalation condition
- evidence source URL and verification date

The entitlement source and route source are separate facts and must remain
separate in the interface and API.

### Curate evidence checklists

Evidence cannot be generated from a generic scheme label. A checklist must be
specific to the issue and official process, sourced, minimal, and clear about
what is optional. Hisaab must never suggest uploading documents to itself.

### Preserve route coverage

All verified grievance rungs and universal routes must remain reachable. The
default can show the first action, but progressive disclosure must not discard
later rungs or their evidence.

### Restore provenance at the presentation boundary

Any route description containing a number, deadline, condition, or authority
must retain its `source_url` and `verified_at`/`scraped_at` through the query,
adapter, API, and component. Area diagnoses must show an as-of date.

## Visual rationale

The anti-slop answer is not louder art direction. It is context-specific
restraint: one task, one clear action, literal labels, adjacent evidence, and no
decorative product theatre. Even Anthropic's frontend-design guidance warns
against generic AI aesthetics and calls for context-specific design; for a
public service, predictability and trust should outrank novelty
([frontend design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md)).

Aptos can be used for Latin text, but Microsoft's published coverage lists Latin,
Greek, Cyrillic, and Vietnamese—not the full Indic-script set. Noto provides
script-specific web fonts and is the safer multilingual foundation
([Aptos](https://learn.microsoft.com/de-at/typography/font-list/aptos),
[Noto usage](https://notofonts.github.io/noto-docs/website/use/)).

## Tenet acceptance matrix

| Tenet | Design gate | Failure example |
| --- | --- | --- |
| Sourced claims | Claim, scope, period, and source are adjacent | A deadline appears only in unsourced prose |
| No misleading claims | Visual language cannot turn aggregate evidence into personal advice | A red district score preselects a person's complaint |
| No CAPTCHA automation | Stop at a clear official handoff | A bot attempts to submit CPGRAMS |
| No lossy refresh | Existing rungs, scope, geography, and money remain covered | A refresh drops an escalation rung or converts unknown money to zero |

These gates also apply to translations, print, shared routes, API responses, and
mobile disclosure states.

## Delivery sequence

1. Run the field study in `USER_RESEARCH_PLAN.md`.
2. Test the three flows with identical, source-locked content.
3. Choose the flow by task performance and harm review, not taste.
4. Add the route semantics and provenance fields without reducing coverage.
5. Build one staged service shell and keep old URLs as state-restoring routes.
6. Release RTE as the complaint-coverage test independent of district data.
7. Validate accessibility, low-connectivity, print, helper, and interruption
   conditions.
8. Run the existing claim, no-loss, test, and publish gates before deployment.

## Decisions that remain open

- Which problem labels match language used by citizens in different states.
- Whether issue-first or a hybrid issue/scheme start produces fewer wrong routes.
- Which preparation details are safe and sufficiently sourced per scheme.
- Which actions deserve a printable or CSC handoff in each scheme.
- Which languages can be maintained as complete, reviewed service variants.
- Whether aggregate evidence helps after the action or creates avoidable doubt.

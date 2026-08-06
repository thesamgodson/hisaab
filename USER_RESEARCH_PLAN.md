# Hisaab citizen research plan

## Purpose

Validate whether Hisaab can help a person move from a welfare problem to a safe,
correct, and usable next action. This study chooses the service sequence and
language. It is not a usability polish exercise and not evidence of population-
level impact.

## Research boundary

Known from desk research:

- Hisaab has source-backed entitlements and verified grievance routes.
- Many official grievance journeys continue across portals, calls, paper,
  offices, receipts, waiting, and escalation.
- Mobile access is common, but ownership, digital confidence, accessibility,
  language, and upload capability are uneven.

Hypotheses to test, not facts:

- People start with a problem description rather than a scheme or district.
- A single dominant first action reduces confusion.
- A script, evidence checklist, and expected receipt are more useful than a
  district score before action.
- Helpers need a printable, non-personal action sheet.
- Area evidence is useful only after the practical route is clear.

Public-service research guidance says assumptions from stakeholders should not
be treated as user needs; teams should observe actual and potential users,
including disabled and low-confidence users
([GOV.UK user needs](https://www.gov.uk/service-manual/user-research/start-by-learning-user-needs),
[discovery research](https://www.gov.uk/service-manual/user-research/user-research-in-discovery)).

## Questions

- How does a person describe the problem before learning its scheme name?
- What do they believe will happen after a call, portal submission, letter, or
  office visit?
- Which authority do they try first, and why?
- What makes a source or instruction credible without imitating government?
- What information do they need before they are willing to act?
- Can they distinguish an entitlement, a grievance route, aggregate area data,
  and a representative's oversight role?
- What do they keep after filing, and how do they decide to escalate?
- How do family members, CSO workers, CSC/VLE workers, and other helpers mediate
  the journey?
- What breaks on a shared phone, low-end Android device, slow connection, large
  text, screen reader, interruption, or printed page?

## Participants

Recruit 12–18 participants for directional discovery and repeated prototype
rounds. This is purposive qualitative sampling, not a nationally representative
survey.

Include:

- 5–7 people who receive or recently sought a pension, ration, wage, housing,
  school, or related welfare benefit.
- 2–3 family or community helpers who regularly act with a beneficiary.
- 2–3 CSO, casework, legal-aid, or social-audit workers.
- 2–3 CSC/VLE, facilitation-centre, or frontline service workers where ethically
  and operationally feasible.
- At least 3 people aged 60 or older.
- At least 3 people who self-report low digital confidence.
- At least 2 disabled participants, including one screen-reader user if possible.

Cover at least one Hindi-speaking and one non-Hindi-speaking state, rural and
urban settings, and more than one supported scheme family. Recruit for varied
gender and device ownership, including people who depend on a shared phone.

Do not claim saturation for “Indian citizens” from this sample. Record which
groups, states, languages, disabilities, and scheme journeys remain untested.

## Ethics and privacy

- Participation is voluntary, compensated, and unrelated to any benefit decision.
- Use informed consent in the participant's preferred supported language.
- Never ask for an Aadhaar number, account number, phone number, grievance text,
  case document, or exact home coordinates in the prototype.
- Use fictional or participant-approved redacted scenarios and artifacts.
- Do not photograph documents or record a session without separate explicit
  consent. Provide a no-recording path.
- Do not enter case details into Hisaab, analytics, URLs, notes, or issue trackers.
- Remove names and specific case identifiers from research notes. Keep the
  consent record separate from study notes.
- Use a trained interpreter or moderator for each language. Do not use live
  machine translation for legal instructions.
- Provide a stop rule and a real support/referral path if a session surfaces an
  urgent grievance. The researcher must not promise resolution.

The product must also make its own data use clear and specific. India's DPDP Act
requires a notice describing the personal data and purpose before or alongside a
request for consent; the safer Hisaab design is to avoid collecting case data in
the first place
([Digital Personal Data Protection Act, section 5](https://www.indiacode.nic.in/show-data?abv=CEN&actid=AC_CEN_45_0_00003_2023-22_1763464807080&orderno=5&sectionno=5&statehandle=123456789%2F1362)).

## Prototype set

Use the same source-locked content and the same two or three scheme scenarios in
all prototypes.

### A — Issue-first companion

`what happened → concrete trigger → area → do this now → prepare → escalate`

### B — Scheme-assisted companion

`problem or scheme → area → do this now → prepare → escalate`

### C — Location-first control

`area → choose a problem → do this now → prepare → evidence → escalate`

Test three presentation treatments only after the sequence is understandable:
action brief, numbered field guide, and plain service form. Do not add gradients,
illustration, cards, or motion to create artificial preference differences.

## Scenarios

Use fictional details but realistic routes:

- MGNREGA wages have not arrived after work was completed.
- A ration shop refused or did not provide the expected ration.
- A PMAY-G instalment appears delayed.
- A school/RTE right or complaint needs action even though local education data
  is available only at state grain.
- A helper needs to print or share a non-personal plan for someone else.

Include one scenario where the first selection is wrong, one where the user goes
Back, one interruption and resume, and one official CAPTCHA handoff. Never ask a
participant to solve or automate the CAPTCHA inside Hisaab.

## Session outline

Allow 45–60 minutes:

1. **Context, 10 minutes:** ask how the participant last sought help, what channel
   they used, who assisted, and what they kept.
2. **First-use task, 15 minutes:** present a scenario and ask the participant to
   think aloud without feature explanation.
3. **Channel handoff, 10 minutes:** ask what they would do next outside Hisaab,
   what they would say or carry, and what proof they expect.
4. **Recovery, 10 minutes:** introduce a wrong choice, interruption, unavailable
   data, or unresolved first step.
5. **Alternative, 10 minutes:** test one different flow with the same scenario.
6. **Debrief, 5 minutes:** ask the participant to explain Hisaab to another person
   and say what they would distrust.

Moderators may clarify the fictional scenario but must not teach the interface,
decode scheme acronyms, point at controls, or describe the intended answer.

## Conditions to test

- Participant's own phone where safe and consented; otherwise a low-end Android
  reference device.
- 320px and 375px viewport widths.
- Slow or interrupted network and a full refresh.
- Browser Back, in-service Back, and resumed shared URL.
- 200% text zoom and large system text.
- Keyboard-only and TalkBack or another screen reader.
- Sunlight/low contrast and one-handed use.
- A4 black-and-white print.
- Helper mode with the beneficiary present and with a fictional handoff.

WCAG is the baseline, not the whole research method. W3C's supplemental guidance
also stresses clear content, predictable structure, and visible page purpose
([WCAG](https://www.w3.org/WAI/standards-guidelines/wcag/),
[clear content](https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/),
[page structure](https://www.w3.org/WAI/WCAG2/supplemental/patterns/o2p03-page-structure/)).

## Observation sheet

For each participant and task, record:

- Language, role, broad device/access context, and scenario—not identity.
- First interpretation of the page.
- Words used for the problem and authority.
- First selected route and whether it is correct for the scenario.
- Points where the participant asks for help, guesses, or abandons.
- Whether they can state the right, next action, preparation, expected proof, and
  escalation in their own words.
- Whether they understand Hisaab is independent and the data is aggregate.
- Whether Back, refresh, print, share, and official handoff preserve the task.
- Accessibility barriers and workarounds.
- Harm signals: false reassurance, fear, disclosure pressure, wrong authority,
  premature escalation, or belief that Hisaab filed the complaint.

Do not record scroll depth, time-on-page, or number of component interactions as
evidence of usefulness.

## Prototype decision rules

Advance a flow only when participants across beneficiary and helper groups can:

- Find the correct first authority without moderator instruction.
- Explain why that action is appropriate without treating area data as a verdict.
- Produce a usable call, copy, print, or visit plan.
- State what proof to keep and what an unresolved next step means.
- Recover from a wrong selection and resume after interruption.
- Recognize the official handoff and understand that Hisaab did not submit the
  grievance.

Treat any of these as a stop-ship issue:

- The interface hides a supported complaint because district data is missing.
- A person believes a district score decides their eligibility or case.
- A route lacks its official source or current verification date.
- A translation changes a right, condition, deadline, or escalation order.
- A participant feels required to disclose personal case data to Hisaab.
- A keyboard, screen-reader, low-connectivity, or print path loses the action.
- Any flow attempts to bypass an official CAPTCHA.

Use prototype targets such as “first authority within 60 seconds” and “prepared
plan within three minutes” only to compare iterations. Do not publish them as
impact until a defined, auditable evaluation supports the claim.

## Synthesis

- Debrief after each session and separate observation from interpretation.
- Cluster findings by service stage, user group, scheme, language, channel, and
  harm—not by UI component.
- Record disconfirming evidence and groups not represented.
- Update problem vocabulary only when the source legal meaning remains intact.
- Trace every accepted change to an observation and every public claim to an
  official source.
- Run at least two rounds so round two can test fixes rather than merely confirm
  the first prototype.

The output is a decision on service sequence, tested problem vocabulary, channel
handoff requirements, accessibility failures, and a prioritized implementation
backlog. It is not a claim that Hisaab has improved benefit delivery.

# Citizen Action Brief — Design Spec

**Date:** 2026-03-30
**Status:** Approved
**Goal:** Transform Hisaab from a data dashboard into a citizen action platform. PIN code in, plain-English diagnosis + verified contacts + complaint paths out.

---

## Core Principle

Every piece of information shown must trace back to an official government source with a URL and scrape date. No exceptions. No LLM-generated content in the core flow — diagnosis is deterministic templates. Same data quality bar as existing scheme data.

---

## 1. Officials Directory (`directory/`)

### Data Sources

| Source | Data | Scrape Method |
|--------|------|---------------|
| District NIC websites (`{district}.nic.in`, state portals) | District Collector, BDO, scheme programme officers | requests + Playwright |
| DARPG / CPGRAMS (`pgportal.gov.in`) | Grievance officer contacts per department | requests |
| Election Commission + MyNeta (existing) | MP/MLA office address, phone | Already scraped (extend) |

### New DB Tables

**`district_officials`**

| Column | Type | Notes |
|--------|------|-------|
| state | TEXT | UPPER CASE |
| district | TEXT | UPPER CASE |
| role | TEXT | "District Collector", "BDO", "MGNREGA Programme Officer", etc. |
| name | TEXT | |
| phone | TEXT | NULL if unavailable |
| email | TEXT | NULL if unavailable |
| office_address | TEXT | NULL if unavailable |
| source_url | TEXT | Required — no record without this |
| scraped_at | TEXT | ISO timestamp, required |

Primary key: `(state, district, role)`

**`grievance_channels`**

| Column | Type | Notes |
|--------|------|-------|
| scheme | TEXT | "MGNREGA", "PMAY-G", etc. |
| level | TEXT | "district", "state", "national" |
| portal_name | TEXT | Human-readable name |
| portal_url | TEXT | Direct link to complaint form |
| phone | TEXT | Helpline number, NULL if none |
| description | TEXT | One-line: what this portal handles |
| escalation_scheme | TEXT | NULL or scheme for next-level escalation |
| source_url | TEXT | Required |
| scraped_at | TEXT | ISO timestamp |

Primary key: `(scheme, level, portal_name)`

### Freshness Rules

- Officials data older than 90 days: show amber warning "This information may be outdated — verify at [source link]"
- Officials data older than 6 months: do not display name/phone, only show "Contact the {role} office — verify at [source link]"
- Grievance channels: checked quarterly (portals are stable)

---

## 2. Action Brief Engine (`action_brief/`)

### Pipeline

```
PIN (6 digits)
  → constituency/mapper.py: resolve district, state
  → constituency/mapper.py: resolve MP, MLA (existing)
  → queries/*: fetch all scheme data for district (existing)
  → briefs/flag_checks.py: detect red flags (existing, 10+ detectors)
  → directory: fetch officials for district (new)
  → directory: fetch grievance channels for flagged schemes (new)
  → action_brief/engine.py: assemble ActionBrief (new)
```

### Data Structures

```python
@dataclass(frozen=True)
class DiagnosisItem:
    severity: str          # "high", "medium", "low"
    scheme: str            # "MGNREGA", "PMAY-G", etc.
    summary: str           # Plain English, one sentence
    detail: str            # Supporting context, one sentence
    amount: str | None     # "Rs 4.2 crore" — formatted for readability
    source_url: str        # Direct link to source data

@dataclass(frozen=True)
class ContactCard:
    role: str              # "Member of Parliament", "District Collector", etc.
    name: str
    phone: str | None
    email: str | None
    office_address: str | None
    relevance: str         # "Oversees all district-level schemes"
    source_url: str
    last_verified: date

@dataclass(frozen=True)
class ActionItem:
    scheme: str
    action: str            # "File a complaint about delayed MGNREGA wages"
    portal_name: str
    portal_url: str
    escalation: str        # "If no response in 30 days, escalate to CPGRAMS"
    escalation_url: str

@dataclass(frozen=True)
class ActionBrief:
    pin: str
    district: str
    state: str
    mp: MPInfo
    mla: MLAInfo
    diagnosis: list[DiagnosisItem]
    contacts: list[ContactCard]
    actions: list[ActionItem]
    scheme_data: dict[str, Any]
    generated_at: datetime
```

### Diagnosis Templates

Rule-based, no LLM. Each red flag pattern maps to a plain-English template.

| Red Flag | Template |
|----------|----------|
| `recovery_rate_pct < 20` | "Only {rate}% of misappropriated MGNREGA funds have been recovered in {district}. Rs {amount} lakhs remains unrecovered." |
| PMAY-G `completion_pct < 50` | "Less than half the sanctioned houses have been built in {district}. {completed} out of {sanctioned} houses completed." |
| JJM `coverage_pct < 50` | "Less than half the households in {district} have tap water connections. {covered} out of {total} households connected." |
| PMGSY `completion_pct < 50` | "{pending} sanctioned roads in {district} are still incomplete out of {total} sanctioned." |
| PM POSHAN `feeding_pct < 60` | "Only {pct}% of enrolled children in {district} are being fed under the mid-day meal scheme." |
| PDS active cards but 0 offtake | "{cards} families have ration cards but no grain distribution recorded this year in {district}." |
| NSAP low pension coverage | "Only {paid} out of {eligible} eligible pensioners received payments in {district}." |
| MGNREGA `cases_reported > 100` | "{cases} complaints have been filed against MGNREGA implementation in {district}." |

Sorted by severity: financial misappropriation > low delivery > data gaps. Maximum 5 items shown.

If no red flags: "No major red flags detected in {district}. Your area is performing at or above state average across tracked schemes."

### Contact Ordering

1. Member of Parliament (always shown)
2. MLA (always shown)
3. District Collector (always shown)
4. Scheme-specific programme officers (only for schemes with red flags)

### Action Items

Only generated for schemes with active red flags. Each maps to:
- The scheme's primary grievance portal
- CPGRAMS (`pgportal.gov.in`) as universal escalation
- RTI portal (`rtionline.gov.in`) as last resort

---

## 3. API

### `GET /api/v1/action/{pin_code}`

Returns the full `ActionBrief` as JSON.

**Response:**
```json
{
  "pin": "221001",
  "district": "VARANASI",
  "state": "UTTAR PRADESH",
  "mp": { "name": "...", "party": "...", "constituency": "..." },
  "mla": { "name": "...", "party": "...", "constituency": "..." },
  "diagnosis": [
    {
      "severity": "high",
      "scheme": "MGNREGA",
      "summary": "Only 8% of misappropriated funds recovered in Varanasi.",
      "detail": "Rs 4.2 crore flagged, Rs 3.9 crore unrecovered.",
      "amount": "Rs 3.9 crore",
      "source_url": "https://nrega.nic.in/..."
    }
  ],
  "contacts": [
    {
      "role": "Member of Parliament",
      "name": "...",
      "phone": "...",
      "email": null,
      "office_address": "...",
      "relevance": "Elected representative for Varanasi constituency",
      "source_url": "https://eci.gov.in/...",
      "last_verified": "2026-03-15"
    }
  ],
  "actions": [
    {
      "scheme": "MGNREGA",
      "action": "File a complaint about fund misappropriation",
      "portal_name": "MGNREGA Public Grievance Portal",
      "portal_url": "https://nrega.nic.in/netnrega/muster_complaint.aspx",
      "escalation": "If no response in 30 days, escalate to CPGRAMS",
      "escalation_url": "https://pgportal.gov.in/"
    }
  ],
  "scheme_data": { "...existing scheme query results..." },
  "generated_at": "2026-03-30T14:30:00Z"
}
```

**Error cases:**
- Invalid PIN (not 6 digits): 400
- PIN not found in mapping: 404 with `{"detail": "PIN code not found. Try a nearby PIN."}`
- District found but no scheme data: 200 with empty diagnosis, contacts still shown

### `GET /api/v1/action/{pin_code}/card`

Returns shareable SVG image.

**Query params:**
- `format=portrait` (default, 1080x1920 — WhatsApp/stories)
- `format=landscape` (1200x630 — Twitter/Telegram/link previews)

**Card content:**
- Header: "HISAAB" + district name + state
- Body: Top 3-4 diagnosis items as one-liners with severity dots
- Contacts: MP + MLA + District Collector names with roles
- Footer: "Enter your PIN at hisaab.info" + generation date + data freshness date

No percentages or jargon on the card. "Rs 4.2 crore unrecovered" not "8% recovery rate".

---

## 4. Frontend

### New Page: `/action/[pin]/page.tsx`

Single page, three layers with progressive disclosure.

#### Layer 1: "What's Wrong" (always visible)

Header card:
- District name + state (large)
- MP: name + party + constituency
- MLA: name + party + constituency

Below header: 3-5 `DiagnosisItem` cards. Each shows:
- Severity indicator (red/amber/green dot)
- `summary` as the headline
- `detail` as supporting text
- "Source" link to `source_url`

If no red flags: green banner with the "no major issues" message.

#### Layer 2: "Who's Responsible" (always visible)

2-column grid (desktop), stacked (mobile). Each `ContactCard` renders:
- Role (bold)
- Name
- Phone: tap-to-call link on mobile (`tel:` href)
- Email: tap-to-email link (`mailto:` href)
- Office address (if available)
- One-line `relevance` note
- "Verified {last_verified}" subtle tag
- Amber warning if >90 days old

#### Layer 3: "What You Can Do" (always visible)

Per-scheme action cards, only for flagged schemes. Each shows:
- Scheme name
- `action` as headline
- Button linking to `portal_url` (opens in new tab)
- `escalation` note with link to `escalation_url`

Universal fallback at bottom: "For any government service complaint, file at CPGRAMS" + "File an RTI request at rtionline.gov.in"

#### Collapsed Section: "Full Data"

Expandable `<details>` or accordion. Contains:
- Existing scheme cards (reuse `SchemeCard.tsx`)
- Money flow summary (reuse existing component)
- This is the current `/district/[name]` content, embedded

#### Share Button

Fixed bottom bar on mobile, top-right on desktop.

On tap:
1. Fetch `/api/v1/action/{pin}/card?format=portrait`
2. Convert SVG → PNG via canvas
3. Mobile: Web Share API (navigator.share) → native share sheet (WhatsApp, Telegram, etc.)
4. Desktop: Download PNG + copy-to-clipboard fallback

### Home Page Changes

- PIN input becomes the hero section (above the fold)
- CTA text: "Check Your Area" or "Enter your PIN code"
- India map + scheme grid move below as "Explore by District" / "Explore by Scheme"
- Existing `/constituency` page remains as secondary entry point
- Navigation: add "Check Your Area" as primary nav item

---

## 5. Shareable Card Design

### Portrait (1080x1920) — WhatsApp/Stories

```
┌──────────────────────────┐
│  HISAAB                  │
│  ━━━━━━━━━━━━━━━━━━━━━━  │
│  VARANASI, UTTAR PRADESH │
│                          │
│  ● Rs 3.9 crore MGNREGA │
│    funds unrecovered     │
│                          │
│  ● 684 houses unbuilt    │
│    under PMAY-G          │
│                          │
│  ● Only 42% households   │
│    have tap water (JJM)  │
│                          │
│  ─────────────────────── │
│  MP: [Name] ([Party])    │
│  MLA: [Name] ([Party])   │
│  DC: [Name]              │
│                          │
│  ─────────────────────── │
│  Enter your PIN at       │
│  hisaab.info             │
│  Data as of 2026-03-05   │
└──────────────────────────┘
```

### Landscape (1200x630) — Twitter/Telegram

```
┌─────────────────────────────────────────────────┐
│  HISAAB   VARANASI, UP        MP: [Name]        │
│  ━━━━━━━━━━━━━━━━━━━━━━━     MLA: [Name]        │
│  ● Rs 3.9cr unrecovered       DC: [Name]        │
│  ● 684 houses unbuilt                           │
│  ● 42% tap water coverage                       │
│  ─────────────────────────────────────────────── │
│  Enter your PIN at hisaab.info  Data: 2026-03-05│
└─────────────────────────────────────────────────┘
```

---

## 6. Testing Strategy

### Unit Tests

- **Diagnosis templates:** Given red flag input X, produces exact English output Y. One test per template.
- **Contact ordering:** Given officials list, produces correct order (MP → MLA → DC → scheme officers).
- **Action items:** Given flagged schemes, produces correct portal URLs and escalation paths.
- **ActionBrief assembly:** Given mock data, produces correct structure.
- **Stale data warnings:** Officials at 91 days → amber warning. At 181 days → name hidden.

### Integration Tests

- **Full pipeline:** PIN → ActionBrief with real DB data.
- **API endpoints:** `/action/{pin}` returns 200 with correct shape. `/action/{pin}/card` returns valid SVG.
- **Error cases:** Invalid PIN → 400, unknown PIN → 404.

### Data Integrity Tests

- Every `grievance_channels` row has a valid `portal_url` that resolves (HTTP 200).
- Every `district_officials` row has a `source_url`.
- No `district_officials` row older than 6 months without the stale flag.

---

## 7. What We're NOT Building

- No LLM in the core action brief path. Deterministic templates only.
- No language localization in this phase. English only.
- No guided complaint filing (pre-filled forms, step-by-step wizards).
- No user accounts, saved reports, or notification subscriptions.
- No scraping of unofficial sources (social media, personal websites).
- No officer photos or biographical information.

---

## 8. Migration Path

Existing pages stay intact:
- `/district/[name]` — unchanged, still works for data-focused users
- `/constituency/[name]` — unchanged, still works for MP report cards
- `/constituency` — unchanged, PIN entry still routes to constituency report

New additions:
- `/action/[pin]` — the citizen action page (new)
- Home page PIN input routes to `/action/[pin]` instead of `/constituency`
- "Check Your Area" becomes primary nav item

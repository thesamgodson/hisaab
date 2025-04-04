# Hisaab Manifesto

Hisaab is public accountability infrastructure.

India's government welfare schemes — MGNREGA, PMGSY, PMAY-G, PM Kisan, Jal Jeevan Mission, PM POSHAN, NSAP, PDS/NFSA — collectively move lakhs of crores to hundreds of millions of citizens. The data is public, but practically inaccessible: fragmented across 8+ portals, brittle tables, no cross-scheme search, weak context, and poor language access.

Hisaab fixes that.

Any citizen should be able to ask in their own language: “Where did the money go?” and get a plain-language answer with a verifiable government source.

## What we are building

1. Data pipeline
- Ingests public data from 8 government schemes: fund flow, expenditure, payment delays, misappropriation, delivery metrics
- Normalizes records into a unified SQLite schema with cross-scheme VIEWs
- Covers: rural employment (MGNREGA), rural roads (PMGSY), rural housing (PMAY-G), farmer payments (PM Kisan), rural water (JJM), school nutrition (PM POSHAN), pensions (NSAP), ration distribution (PDS/NFSA)

2. Knowledge base
- Organizes records by scheme → state → district
- Preserves provenance for every claim (URL, scrape time, parser version)
- Cross-scheme queries: “How much money flows to district X across all schemes?”

3. Citizen interface
- Multilingual, mobile-first
- Returns direct answers with shareable official evidence links
- Journalist briefs with red flags per district

## In practice

A woman in Tiruvannamalai asks why wages are delayed.
Hisaab returns local MGNREGA records, unresolved amounts, FTO pendency, and the exact government source.

A journalist in Bihar asks which districts have the worst road completion.
Hisaab returns PMGSY data ranked by completion rate, with source URLs.

A citizen in Cuddalore asks how many schemes serve their district.
Hisaab returns a cross-scheme brief covering all 8 schemes with red flags.

## What this is not

- Not a growth startup
- Not a portfolio project

## What this is

- Open, auditable, permanent public digital infrastructure for accountability

## Non-negotiable rule

No public numeric claim is published without source and date in `DATA_CLAIMS.md` (or generated claim artifacts that follow the same schema).

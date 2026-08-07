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
- Lets people read several schemes for one area without adding incompatible
  money stages, periods, units, or geographic grains into a false total

3. Citizen interface
- Mobile-first and area-first: one public welfare account, not three products
- Returns exact public records with source, record date, retrieval date, grain,
  caveat, and claim ID
- Names missing or state-only data instead of turning absence into zero
- Keeps verified rights and official complaint routes beside the evidence,
  while leaving the citizen to choose the issue

## In practice

A worker in Tiruvannamalai asks why wages are delayed.
Hisaab shows the district MGNREGA financial and FTO process records with their
periods and sources, then the sourced wage entitlement and every verified
official route. It does not pretend that an area total proves the worker's
individual payment status.

A journalist in Bihar asks which districts have the worst road completion.
Hisaab lets the journalist compare the same PMGSY road-count and road-length
fields for the same programme period, with project value and expenditure kept
separate and every source attached.

A citizen in Cuddalore wants to understand the area's welfare account.
Hisaab shows each available district record in its own terms, separates state
context, names coverage gaps, and lets the citizen choose a service to see its
rights and official routes.

## What this is not

- Not a growth startup
- Not a portfolio project
- Not a government service, eligibility checker, wrongdoing verdict, or
  automated complaint filer

## What this is

- Open, auditable, permanent public digital infrastructure for accountability

## Non-negotiable rules

1. No public claim is published without a source and date in `DATA_CLAIMS.md`
   or a generated claim artifact that follows the same schema.
2. A true number is never relabelled, totalled, ranked, or visually emphasized
   in a way that outruns its source.
3. Hisaab never automates a CAPTCHA or submits a person's complaint.
4. A refresh never reduces geographic grain, coverage, detail, or money.

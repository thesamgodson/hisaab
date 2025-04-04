# Data Claims Register

This file is the source-of-truth register for headline/public claims.

Rule: if a number appears in public docs, demos, deck, website, or bot responses, it must exist here with source and date.

## Schema

Each claim must include:

- `claim_id`: stable id (e.g. `CLAIM-2026-0001`)
- `statement`: human-readable claim sentence
- `value`: numeric value
- `unit`: `INR`, `cases`, `%`, etc.
- `as_of_date`: date the claim refers to (`YYYY-MM-DD`)
- `geography`: India / state / district / block / panchayat
- `source_title`: report/page title
- `source_url`: canonical source URL
- `retrieved_at_utc`: scrape/retrieval timestamp
- `retrieval_method`: `requests`, `interactive_browser`, `manual`, etc.
- `dataset_artifact`: local file path (`data/...` or `reports/...`)
- `parser_version`: script/version used
- `confidence`: `high|medium|low`
- `status`: `active|superseded|disputed`
- `notes`: caveats, definition details

## Claims

| claim_id | statement | value | unit | as_of_date | geography | source_title | source_url | retrieved_at_utc | retrieval_method | dataset_artifact | parser_version | confidence | status | notes |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| CLAIM-PLACEHOLDER-001 | Replace with verified claim text | 0 | INR | 2026-03-04 | India | Replace with source title | https://example.gov | 2026-03-04T00:00:00Z | requests | data/curated/example.json | scrape_misappropriation.py@v0.2 | low | superseded | Placeholder row. Do not publish. |

## Usage policy

- Update or append claims after every material data refresh.
- Never delete old claims; mark them `superseded` with notes.
- If two official pages disagree, keep both with `disputed` status and explain in notes.
- Any answer shown to citizens must include claim + source URL + as-of date.

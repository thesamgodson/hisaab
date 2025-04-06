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
| CLAIM-2026-0001 | MGNREGA social audits reported Rs 2,301.52 crore in misappropriation across 32 states in FY 2024-25 | 2301521185 | INR (lakhs raw) | 2026-03-04 | India | MGNREGA Social Audit — Recovery Report | https://mnregaweb4.nic.in/netnrega/SocialAuditFindings/SAU_FMRecoveryReport.aspx | 2026-03-04T20:08:58Z | requests | data/curated/misappropriation_*_latest.json | scrape_misappropriation.py | high | active | amount_reported summed across all districts and 32 states. Value is in the native unit of the portal (lakhs); divide by 100 for crores. |
| CLAIM-2026-0002 | 108,403 of 110,238 sanctioned PMGSY roads completed nationally (98.3%) across 32 states | 108403 | roads | 2026-03-06 | India | PMGSY Citizen District Brief Details | https://pmgsy.dord.gov.in/MvcReportViewer.aspx | 2026-03-06T03:24:27Z | requests | data/curated/pmgsy_district_*_latest.json | scrape_pmgsy_catalog.py | high | active | Cumulative sanctioned vs completed across all scheme types and districts in 32 states. |
| CLAIM-2026-0003 | 2.46 million of 8.04 million PMAY-G houses completed nationally (30.6%) across 29 states in FY 2024-25 | 2460480 | houses | 2026-03-06 | India | PMAY-G Physical Progress Report | https://report.pmayg.dord.gov.in/netiay/DataAnalytics/PhysicalProgressRpt.aspx | 2026-03-06T04:04:08Z | requests | data/curated/pmayg_district_*_latest.json | scrape_geo_hierarchy.py | medium | active | Delivery metric only; financial data (funds_released/utilized) is zeros — portal behind login/Power BI. |
| CLAIM-2026-0004 | 96.47 million PM Kisan beneficiaries paid Rs 80,313.56 crore across 36 states in FY 2024-25 | 96465711 | beneficiaries | 2026-03-06 | India | PM Kisan Dashboard | https://pmkisan.gov.in | 2026-03-06T05:33:32Z | requests | data/curated/pmkisan_district_*_latest.json | scrape_geo_hierarchy.py | high | active | 28 of 36 states report district='ALL' only (no sub-state breakout). amount_paid_lakhs = 8,031,356 lakhs. |
| CLAIM-2026-0005 | 15.82 crore Jal Jeevan Mission tap connections provided to 19.36 crore rural households (81.7% coverage) across 34 states | 158185179 | tap connections | 2026-03-06 | India | JJM District View Report | https://ejalshakti.gov.in/jjmreport/JJMDistrictView.aspx | 2026-03-06T04:34:20Z | requests | data/curated/jjm_district_*_latest.json | scrape_geo_hierarchy.py | medium | active | Delivery metric only; funds_released/utilized are zeros — no financial API endpoint found. |
| CLAIM-2026-0006 | 43.66 lakh children fed under PM POSHAN against 10.99 crore enrolled across 34 states in FY 2024-25 | 4366252 | children fed | 2026-03-06 | India | PM POSHAN AMS Portal | https://pmposhan-ams.education.gov.in/Reported_ams_School.aspx | 2026-03-06T05:49:15Z | requests | data/curated/pmposhan_district_*_latest.json | scrape_pmposhan.py | medium | active | children_fed is a daily reporting figure, not cumulative. Funds columns are zeros — hardcoded in scraper. Low fed/enrolled ratio is expected (daily snapshot vs total enrollment). |
| CLAIM-2026-0007 | 3.18 crore NSAP pension beneficiaries paid, ~Rs 8,649 Cr estimated central pension (imputed) across 36 states in FY 2024-25 | 31837292 | beneficiaries | 2026-03-06 | India | NSAP via data.gov.in API | https://api.data.gov.in/resource/nsap | 2026-03-06T06:07:11Z | requests | data/curated/nsap_district_*_latest.json | scrape_nsap_api.py | medium | active | Financial amounts IMPUTED: beneficiaries × GoI central pension rate × 12. Rates: IGNOAPS Rs 200/mo, IGNWPS Rs 300/mo, IGNDPS Rs 300/mo. These are central share only; actual disbursement may be higher with state top-ups. |
| CLAIM-2026-0008 | 19.99 crore ration cards recorded under NFSA across 36 states in FY 2024-25 | 199901967 | ration cards | 2026-03-06 | India | NFSA Public Dashboard | https://nfsa.gov.in/public/nfsadashboard/PublicRCDashboard.aspx | 2026-03-06T04:52:37Z | requests | data/curated/nfsa_district_*_latest.json | scrape_geo_hierarchy.py | low | active | Ration card counts only; allocation_mt/offtake_mt are zeros. NFSA dashboard data is stale (Jul 2021 vintage). active = total (no distinction scraped). |

## Usage policy

- Update or append claims after every material data refresh.
- Never delete old claims; mark them `superseded` with notes.
- If two official pages disagree, keep both with `disputed` status and explain in notes.
- Any answer shown to citizens must include claim + source URL + as-of date.

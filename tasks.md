# Tasks — Hisaab

Action log: what was done, outcome, follow-ups. One entry per completed/abandoned unit of work.

### 2026-08-05 — mp_info migration + the state-blind civic-identity family it exposed
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `db/schema.py` (mp_info + constituency_district UNIQUE incl. state), `db/normalize_states.py` (VINTAGE_STATE_EQUIV + candidate_states, canonical Python home), `constituency/{mapper,ingest,report_card}.py`, `action_brief/engine.py`, `api/routes/constituency.py`, `scripts/{clean_pin_constituency,gen_district_aliases}.py`, `db/district_aliases.py` (184), `web/src/lib/{vintage-states,report-card,action-brief}.ts`, `web/src/app/api/v1/{mp/[name],constituency/[name],pin/[pin_code]}/route.ts`, `tests/test_constituency.py` (+11), `DATA_CLAIMS.md` (0035 + 0004 note), trio

Closed handoff #3 and the sibling defects the migration test flushed out. mp_info → UNIQUE(constituency, state), re-ingested 543/543 (3 recovered: Sinha/Aurangabad-Bihar, Sigriwal/Maharajganj-Bihar, Thakur/Hamirpur-HP); web + FastAPI mp/constituency routes state-aware — ambiguous name without ?state= answers 300 with candidates, report cards never merge two states' districts; same fixes in mapper/engine twins. Found en route: constituency_district's UNIQUE also lacked state (HAMIRPUR-HP lost its home-district row; 1,005→1,007), and civic ingest normalized districts through fuzzy_match's state-BLIND alias dict — 26 Bihar PINs served under Maharashtra's CHHATRAPATI SAMBHAJINAGAR, NEW DELHI folded into "DELHI", 181 PINs total re-joined to scheme data after re-ingest with the canonical state-scoped normalizer (pins/pc/ac rebuilt from cache, diffed against snapshot). Shared PC/AC name normalizer (handles datameet's no-space "(SC)" family, ~13 seats) now single-sourced per language: PC_NAME_NORM_SQL ↔ pcNameNorm. Registry +("GUJARAT","DOHAD")→DAHOD: scores de-fragment 945→944/year, DAHOD FY2024-25 corrected 77.8→70.1. Gates: 535 pytest, ruff, tsc, lint, credential-free build all green. Published (dbc3190 pushed, CI green 1m07s; sync_turso 34 tables / 62,712 rows verified) and prod-smoked 11/11: /mp/AURANGABAD → 300 + candidates; ?state=BIHAR → Sinha with Bihar-only card; 804402 precise → AURANGABAD/Sinha; 174305 → Thakur (action brief MP+MLA non-null); /mp/GAYA?state=BIHAR card no longer empty (suffix fix, score 81.1); /constituency/HAMIRPUR → 300, ?state=HP → Thakur incl. recovered home district; regressions 823001 (Manjhi) + 500003 (7/7 MLAs, Kishan Reddy) intact. Follow-ups logged: PC-name registry for 34 unmatched datameet rows (truncations/renames/mojibake), district-fragment folds (PANCH MAHALS-class, Sikkim renames — dedicated pass).

### 2026-08-04 21:15 — Live data refresh: FY2025-26 + 2026 assemblies on production
**Agent:** Claude Code
**Status:** ✅ done
**Files:** scrapers/* (ROOT_DIR fix ×20, MyNeta 2026 slugs, timeouts), db/loaders.py (record-wins fin_year + format canon), queries/composite.py (multi-year persist, cumulative-as-evergreen), constituency/ingest.py (wholesale assembly replace), web fin-year dynamics, DATA_CLAIMS.md (+5 claims, 3 superseded)

Refreshed 6 of 11 schemes to 2026-08-04 (PMGSY, PMAY-G FY25-26, JJM, PM POSHAN, SBM-G, UDISE+ 2025-26) + all politicians: 4,095 MLAs incl. the five 2026 assemblies, verified on prod (Villivakkam→Aadhav Arjuna). Blocked by government outages, kept at honest March vintage: MGNREGA (nreganarep TCP-dead), NRLM (domain 404), NSAP+all data.gov.in finance (platform timeouts); PM Kisan/NFSA district have no live endpoint. Found+fixed en route: 20 scrapers writing to phantom scrapers/data/, MyNeta map serving 2021 assemblies, loader param-stamping that would relabel old data with new years, 86 orphaned MLAs from delimitation renames, alias-registry monotonic guard silently broken. Prod smoke 13/13; freshness endpoint shows true per-scheme dates.

### 2026-08-04 17:30 — Full overhaul: pipeline, canonical districts, unified scoring, prod resurrection
**Agent:** Claude Code
**Status:** ✅ done
**Files:** run_all.py, states.json, db/normalize_districts.py, db/district_aliases.py, db/schema.py, queries/composite.py, queries/common.py, scripts/{sync_turso,gen_district_aliases}.py, api/routes/freshness.py, DATA_CLAIMS.md, .github/workflows/{ci,refresh-data}.yml, web/src/** (7 commits, e5be9f7..12c3e70)

Executed the approved overhaul end-to-end. Root cause of the 4-month prod outage: the live deployment was built Apr 8 from PR #1 (district_lineage, merged on GitHub but never pulled locally) and its table was never created in Turso — found via vercel logs, reconciled by rebase, feature now live. Shipped: pipeline resurrection (states.json restore + importlib fix + truncate-before-load), canonical district registry (167 aliases; PIN joins 96.9%→99.0%), precomputed district_scores as the single scoring implementation (min-3-schemes confidence floor), scripts/sync_turso.py (34 tables / 61,284 rows verified on Turso), honest-metrics pass (no invented percentages; misleading labels/diagnoses/rankings removed), 8 backfilled DATA_CLAIMS + 2 derived, freshness covering all 11 schemes, CI with DB fixture + ruff + typecheck, weekly refresh workflow with prod smoke probes, dead-code cleanup + docs rewritten to the real architecture. Verification: 501 pytest green, ruff clean, tsc clean, next build clean, 25/25 prod smoke tests pass. Follow-ups: data still 2026-03 vintage (first scheduled refresh will validate scrapers against current portal markup); district_officials still empty (contacts layer); alerts/ and llm/ remain parked.

### 2026-08-04 12:10 — Full project state analysis (overhaul kickoff)
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `findings.md`, `learnings.md`

Sam kicked off an overhaul. Ran full-repo analysis: pytest (500 passed, 4 skipped), web tsc + next build (clean), live prod probes (hisaab-one.vercel.app), DB audits, plus three parallel subsystem sweeps (frontend / Python / data pipeline). Verdict: hero PIN flow dead on prod (Turso missing pin tables, no sync path), all 11 schemes 4-5 months stale, district identity non-canonical, duplicated+diverging business logic (two scoring formulas live), silent `__import__` bug disabling 9 of 11 scheme refreshes. Full inventory in findings.md; overhaul plan delivered to Sam for direction.

### 2026-08-04 17:55 — MGNREGA scraper re-sourced onto the un-gated citizen portal
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `scrapers/scrape_reports.py`, `run_all.py`, `DATA_CLAIMS.md`, `queries/common.py`, `web/src/lib/data-quality.ts`, `CLAUDE.md`, `README.md`

The Aug 2026 `*.nic.in` → `*.dord.gov.in` move put the national MIS report index (`MISreport4.aspx`) behind a captcha, killing the old Playwright scraper (which solved that captcha from a hidden field). Rewrote its session layer onto the public state citizen page `mnregaweb2.dord.gov.in/netnrega/homestciti.aspx`: plain `requests`, an ASP.NET postback on the page's own `fin_year` dropdown to mint Digest-signed report URLs for the target FY, then fetch + parse. Playwright and every line of captcha handling are gone; all five parsers kept verbatim. Recovered 3 of 5 datasets — `financial_statement` and `fto_status` at district level, `fto_pendency` at bank level (portal design). `misappropriation` and `issues_reported` are unreachable un-gated and are now declared as such in `UNAVAILABLE_REPORTS` rather than silently emitting empty files. Verified: BIHAR 38+38+3 and KERALA 14+14+3 records for FY2025-26, loaded via `run_all.py --load-only`, `scraped_at` today, every `source_url` replayable in a cold session. ruff clean, 511 pytest green.

### 2026-08-04 19:05 — MGNREGA FY2025-26 refreshed nationwide (36 states) and live on prod
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `data/curated/{financial_statement,fto_status,fto_pendency}_*_latest.json` (97 files), `data/hisaab.db`, Turso

Looped the citizen-portal scraper over the 34 states beyond Bihar/Kerala: 30 exited fully clean; Chandigarh/Delhi/Lakshadweep are UTs with legitimately empty reports (no-op guard left old files intact) and West Bengal's empty fto_status is portal truth (fund freeze — March scrape was also 0 rows; verified against raw HTML before accepting). Diffed all 97 changed curated files against git HEAD: zero row-count drops, zero granularity loss, 9 net-new UT files. Loaded (financial_statement 749 rows / 35 states, all FY2025-26), scores recomputed (947 districts × 2 years), synced Turso (34 tables / 81,058 rows verified), deployed, smoke 4/4, /api/v1/freshness now reports MGNREGA 2026-08-04. Follow-up: freshness `source` label still says nrega.nic.in — update to the dord.gov.in citizen portal alongside the DATA_CLAIMS pass.

### 2026-08-04 19:55 — DAY-NRLM re-sourced onto LokOS CDN at DISTRICT level (757 districts, Odisha recovered)
**Agent:** Claude Code (+ nrlm-discovery subagent)
**Status:** ✅ done
**Files:** `scrapers/scrape_nrlm.py` (LokOS rewrite), `run_all.py`, `scripts/gen_district_aliases.py`, `db/district_aliases.py` (168→181), `db/normalize_states.py`, `DATA_CLAIMS.md` (0027 + 0024/0010 corrections), freshness labels ×3

Discovery agent read lokos.in's Angular bundles and found the district-level feed the earlier probes missed: cdn.lokos.in/lokos-in/fdm/prod/{SC}/DISTRICT_FDM_{REPORT}.json, where {SC} is LokOS's own 2-letter code (BH not BR). Rewrote scrape_nrlm.py onto it: plain requests (Playwright path was dead with nrlm.gov.in), OVERALL+REVOLVINGFUND merged on districtId, formation-breakdown columns carried forward frozen (LokOS doesn't publish them; none is served publicly), and a granularity guard that refuses any snapshot with fewer (state,district) pairs — the state-level regression can't recur. 741→757 rows verified (Odisha's 30 districts back after 4 months absent), district sums exactly match the national feed, ARARIA spot-check matches the agent's independent fetch. Aliases: Odisha spelling unification (BALESHWAR/BALANGIR/KENDUJHAR/KHORDHA/NUAPADA canon per PIN directory), GAYAJI→GAYA (fixed live scores fragmentation from today's MGNREGA refresh), SRIBHUMI/BENGALURU SOUTH/DHARWAR/ALIPURUDUAR; scores de-fragmented 947→941 districts.

### 2026-08-04 19:58 — data.gov.in recovered: NSAP district revised + 3 finance datasets re-verified
**Agent:** datagovin-retry subagent (verification + claims: Claude Code)
**Status:** ✅ done
**Files:** `data/curated/nsap_district_*` (37 files), `nsap_finance/nfsa_allocation/jjm_allocation_all_latest.json`, `DATA_CLAIMS.md` (0028, re-verification notes on 0013/0014/0015)

Platform recovered from yesterday's timeouts. NSAP district genuinely revised upstream (1,027/2,173 rows changed; total paid 3.18→3.17 crore, still FY2024-25). nsap_finance/nfsa_allocation/jjm_allocation byte-identical upstream — noted as re-verified, no new claims minted. Found upstream now double-lists Assam's renamed Karimganj (KARIMGANJ + SRIBHUMI, near-identical rows); the new alias dedupes on load, claim 0028 documents the ~17.6k double-count. All 40 changed files diffed vs HEAD: zero drops. NOTE: these files went live via the NRLM load+sync before my diff pass finished — sequencing lesson recorded in learnings.md.

### 2026-08-04 20:35 — PM Kisan + NFSA district re-sourced live; NSAP moved to FY2025-26; data.gov.in client fixed
**Agent:** Claude Code (+ pmkisan-nfsa-hunt, datagovin-retry subagents)
**Status:** ✅ done
**Files:** `scrapers/{scrape_pmkisan,scrape_nfsa,scrape_nsap_api,io_utils}.py`, `scrapers/scrape_pmayg_dashboard.py`, `run_all.py`, `queries/common.py`, `web/src/lib/data-quality.ts`, `CLAUDE.md`, `DATA_CLAIMS.md` (0029-0032 + supersessions), `data/curated/` (pmkisan 37 files, nfsa 36, nsap 37)

NFSA district: re-sourced onto the dashboard's own un-gated AJAX handler (one POST, whole country) — 744 districts, +315k cards vs March, fin_year now honestly 'cumulative' with per-row date_of_data (heterogeneous at source: 375 districts report 2026, a tail still 2019-2021). PM Kisan: district coverage 8→36 states via the data.gov.in village dataset aggregated per census StateCode (the API caps pagination at offset 500k SILENTLY — a national pull truncated at 78% and was discarded; per-state partitioning + a ceiling guard now in the scraper); 9.43 crore beneficiaries, installment 22, counts only; homepage state totals FY2026-27 added (mid-cycle caveat); the 8 states' frozen FY2024-25 money rows carried under guards that refuse money-losing writes. NSAP: upstream HAS FY2025-26 (retry agent's find — my claim note 0028 said otherwise and was corrected via dated supersession); pulled it: 2,196 served rows / 744 districts, imputation re-flagged as annualized-projection. Plus the agent-found defects fixed: run_all finance wiring downgrade (jjm→ejalshakti scraper; pmayg deliberately unwired — its only scraper OCRs a captcha, forbidden by standing decision, table frozen with claim caveat), datagov_session() (browser UA + 429 retry) across all six data.gov.in scrapers, NSAP partial-write bug now raises. All gates green; synced (81,909 rows), deployed, freshness: ALL 11 SCHEMES 2026-08-04.

### 2026-08-04 22:30 — Refresh-path hardening: NSAP auto-FY, NSAP wired into run_all, workflow acceptance gate
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `scrapers/io_utils.py` (FY helpers + datagov_api_key), `scrapers/scrape_nsap_api.py`, `run_all.py`, `scripts/verify_refresh.py` (new), `.github/workflows/refresh-data.yml`

Closed HANDOFF follow-up #5 (first-scheduled-refresh readiness). NSAP's hardcoded `--fin-year 2024-2025` default replaced with auto-resolution: `current_indian_fy()` (IST-correct) → probe data.gov.in → fall back to the latest year that actually publishes. Proven live: it resolves 2026-2027 (upstream already has June-2026 rows), but that pull covers only 725 distinct (state,district) pairs vs the existing 744, so the new NRLM-style coverage guard REFUSED it and kept complete FY2025-26 — auto-tracking + no-downgrade both verified. NSAP district was NOT wired into run_all at all (only a dead CSV path); added an explicit `nsap` live branch calling `process_live()`. run_all's `--fin-year` default is now `last_complete_indian_fy()` (=2025-2026 today) so the weekly cron scrapes the last COMPLETE FY for cumulative-annual schemes (MGNREGA/PMAY-G) instead of a stale hardcode or a partial running year (portal probe confirmed the citizen page offers 2026-2027 as default — pulling it would replace a complete year with 4 months). Empirically MGNREGA FY handling is a babysit "fix-what-breaks" item. New `scripts/verify_refresh.py` diffs curated vs HEAD for the three documented regressions (granularity/coverage/money), tested both ways (flags all three, passes clean revisions + <15% churn); wired into refresh-data.yml with `--revert-regressions` (regressed files revert to last-good, clean schemes still publish). Workflow default schemes `jjm,sbm,udise,mgnrega,pmgsy` → `all` (the cron was skipping every new live path: NFSA/NRLM/PM Kisan/NSAP); timeout 120→150. `--load-only` rebuild clean, district_scores unchanged {2024-2025:947, 2025-2026:947}, ruff green. Workflow dispatch/babysit deferred to end of session (after all code lands, to avoid the auto-commit racing my commits).

### 2026-08-04 22:45 — Small items: DATA_GOV_IN_API_KEY env override + PM Kisan double-slug tidy
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `scrapers/io_utils.py`, all 7 data.gov.in scrapers, `scrapers/scrape_pmkisan.py`, `data/curated/pmkisan_district_the-dadra-*` (2 files → 1)

HANDOFF follow-up #4 (partial) + #7. Centralized the data.gov.in demo key into `io_utils.datagov_api_key()` with a `DATA_GOV_IN_API_KEY` env override (demo key stays the fallback; Sam registers the project key himself); threaded through all 7 scrapers that hit data.gov.in (nsap_api/nsap_finance/nfsa_finance/pmposhan_finance/jjm_finance/pmayg_dashboard/pmkisan) — one env var now lifts the rate-limit ceiling everywhere. PM Kisan `state_slug` now collapses internal whitespace (`re.sub(r"\s+","-",...)`) so the homepage's double-spaced "…HAVELI AND  DAMAN…" slugs identically to the village dataset's single-spaced form — was writing two curated files (`…and--daman…` + `…and-daman…`) that BOTH matched the loader glob and double-counted the UT. Reconciled the existing orphan: merged its lone FY2026-27 ALL row into the single-hyphen file (4 rows, one canonical state), deleted the orphan. Every single-spaced state name is byte-identical, so 35 filenames stay stable. Verified: pmkisan DD&DNH now one state / 4 rows after load.

### 2026-08-04 23:20 — LokOS district CIF money wired into the DAY-NRLM story
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `scrapers/scrape_nrlm.py`, `db/schema.py` (nrlm_district +3 cols, scheme_finance +NRLM row, money_flow), `db/loaders.py`, `queries/common.py` ↔ `web/src/lib/data-quality.ts`, `DATA_CLAIMS.md` (0033 + 0027 note), `CLAUDE.md`

Closed HANDOFF follow-up #2. `DISTRICT_FDM_COMMUNITYINVESTMENTFUND.json` (same LokOS grammar + 2-letter codes as RF) merged into the scraper alongside REVOLVINGFUND: 3 new nrlm_district columns (cif_amount_lakhs, cif_shgs_provided, cif_shgs_eligible). CIF is a MAJOR district money metric — **Rs 33,144.83 crore nationally, 3.6× the RF's Rs 9,166.79 cr** — and carries a built-in accountability gap: only 3,056,708 of 9,291,125 eligible SHGs (32.9%) have received it. money_flow + scheme_finance now report NRLM `released_lakhs` = RF+CIF (Rs 42,311.62 cr combined); the table keeps both columns distinct. DAY-NRLM added to scheme_finance for the first time with utilization_pct=NULL, which composite.py filters out (`WHERE utilization_pct IS NOT NULL`) — so scoring is untouched: verified score-invariant, 1,894 district_scores rows byte-identical before/after. Curated diff vs HEAD: purely additive (757→757 districts, RF sum unchanged, 4 new fields). CLAIM-2026-0033 minted (extends, not supersedes, 0027); caveats updated in lockstep. ruff clean; full gates pending the pre-commit batch.

### 2026-08-04 23:55 — Rename-migration pass: canon flipped to official names + civic re-seed + 2 bugs fixed
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `scripts/gen_district_aliases.py` (_OVERRIDES flipped), `db/district_aliases.py` (regenerated, 183), `web/public/india-districts.topojson`, `scripts/sync_turso.py` (empty-table guard), `data/curated/{misappropriation,issues_reported}_*_latest.json` (fin_year stamped), all civic tables re-seeded

Closed HANDOFF follow-up #3. Flipped canon to the official post-rename names in ONE sweep: **GAYA→GAYAJI (Bihar), KARIMGANJ→SRIBHUMI (Assam), RAMANAGARA→BENGALURU SOUTH (Karnataka)** — the reverse of the temporary NEW→OLD aliases. Mechanics: the monotonic guard would have cycled (GAYAJI→GAYA + GAYA→GAYAJI), so I removed the 3 stale reverse aliases from the generated file, flipped `_OVERRIDES` into the AYODHYA/PRAYAGRAJ section, and regenerated (183 aliases, no cycle; RAMNAGAR variant also folds to BENGALURU SOUTH). Updated topojson properties precisely (GAYA→GAYAJI, KARIMGANJ→SRIBHUMI; Ramanagara has no polygon — the frontend applies NO aliases, so the map data must carry canon). normalize_civic_tables folds the seed's old names automatically. Verified end-to-end: PIN 823001 → GAYAJI, lineage BENGALURU SOUTH ← Bangalore Rural, GAYAJI scores A/83, zero old-name leftovers, map join topojson↔score aligned. Districts 947→945 (bonus merges BALOTARA→BALOTRA, GYALSING→GYALSHING from the regen — better canonicalization, not fragmentation).

Two bugs found and fixed en route: (1) **`rm hisaab.db` wiped the civic tables** (pin_district_mapping/constituency/ac/mp/mla/lineage are seeded by `constituency.ingest`, NOT `--load-only`) — re-seeded all from local cache (21,089 PINs, 4,059 AC, 4,104 MLAs, 201 lineage) + loaded the orphan pin_constituency (19,169 rows, no loader wired — a pre-existing gap for item 5). (2) **`sync_turso` had no wipe protection**: a from-scratch DB build that skipped civic re-seed would DROP+recreate empty civic tables on prod — the exact March disaster. Added an empty-local-table guard (never replace a populated remote table with an empty local one; verification treats them as KEPT). This also exposed a **latent refresh-workflow bug**: it only runs `--mla-only`/`--mp-only`, so a scheduled run on a fresh CI DB would have wiped prod's PINs — the sync guard now makes it safe.

### 2026-08-05 00:10 — Provenance fix: frozen social-audit data now self-describes its FY
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `data/curated/{misappropriation,issues_reported}_*_latest.json` (64 files, 1,476 rows)

Caught by 4 regressed api tests during the item-4 gate: my run_all `--fin-year` default change (2024-2025→2025-2026, correct for scraping) silently RELABELED the frozen FY2024-25 misappropriation + issues_reported as FY2025-26, because those curated files carry NO fin_year field and the loader falls back to the param. That's a misleading-claim tenet violation (CLAIM-2026-0001 pins them to FY2024-25) AND it broke the MGNREGA `worst` query (which reads misappropriation at the api's default 2024-2025). Fixed at the data layer per landmine #3: stamped `fin_year=2024-2025` into all 1,476 rows so they're self-describing and no fallback can ever mislabel them again. run_all default stays last_complete FY (safe now — no loaded scheme record lacks fin_year). 511 pytest green, verify_refresh clean (additive field), ruff clean.

### 2026-08-05 00:35 — March-audit defect sweep: verified all vs current code
**Agent:** Claude Code (+ defect-verifier subagent cross-check)
**Status:** ✅ done
**Files:** (verification only — no functional survivors to fix)

### 2026-08-05 02:05 — Refresh-workflow babysit: CI env validated + demo-key throttle finding & fix
**Agent:** Claude Code
**Status:** ✅ done (with a documented finding)
**Files:** `.github/workflows/refresh-data.yml` (weekly default excludes pmkisan), `queries/common.py` ↔ `web/src/lib/data-quality.ts` (PMAY-G provenance caveat corrected)

Closed HANDOFF follow-up (babysit the weekly pipeline). Triggered refresh-data.yml via workflow_dispatch. VALIDATED: the CI environment builds and runs every scraper cleanly (py3.14, Playwright install, all imports resolve — the scrape step executes without error). FINDING: the shared **data.gov.in demo key is heavily 429-throttled in CI** — PM Kisan's ~13M-row village pull stalled ~40 min (cancelled at 42m), and a lean run (nfsa,nrlm,jjm,sbm,udise) also dragged on the data.gov.in finance scrapers. FIX: removed pmkisan (quarterly data) from the weekly cron default (e19f780); the real fix for the rest is registering DATA_GOV_IN_API_KEY (threading complete — just needs the key). The verify_refresh gate + sync_turso wipe-guard were validated LOCALLY (both directions); their CI-only exercise is blocked behind the throttled scrape — deferred to the next session's first real Sunday cron. Also corrected en route: the served PMAY-G finance caveat wrongly said "from data.gov.in" (it's the B.3 report) — fixed in lockstep (4dcffc2). Prod smoke green throughout.

### 2026-08-05 01:40 — PMAY-G finance UN-FROZEN: captcha removed, scraper re-sourced to plain requests
**Agent:** Claude Code (+ pmayg-recon2 subagent, whose late report was the key)
**Status:** ✅ done
**Files:** `scrapers/scrape_pmayg_finance.py` (full rewrite), `run_all.py` (re-wired FINANCE_SCRAPERS), `DATA_CLAIMS.md` (0034 + 0016 superseded), `CLAUDE.md`, `data/curated/pmayg_finance_all_latest.json`

REVERSAL of the item-1 "inconclusive" entry below: the pmayg-recon2 agent I'd stopped as "stuck" had actually FINISHED — its detailed report (delivered via mailbox after the stop) reported the **arithmetic captcha is GONE from the B.3 report** (Report_HighLevel_FinancialProgress.aspx). Independently VERIFIED before acting (Argus — agent output is untrusted): 0 captcha controls on the live page, the GET + 3-POST __VIEWSTATE-relay chain returns the finance grid, and Bihar/Maharashtra/Kerala FY2024-25 match the frozen curated EXACTLY (Bihar released 115935.68). Rewrote scrape_pmayg_finance.py off the forbidden Playwright+Tesseract-OCR path to plain stateless requests (~150 captcha lines deleted; it now ABORTS if a captcha control ever reappears), re-wired into run_all FINANCE_SCRAPERS (was deliberately unwired). Re-scraped all 8 FYs: 214 records / 32 states, coverage held, **36 rows carry upstream corrections since the 2026-03-21 freeze** — the table is UNFROZEN. CLAIM-2026-0034 supersedes 0016; CLAUDE.md updated. 511 pytest green, ruff clean. The route also exposes district-level PMAY-G utilization + an SNA all-schemes report (FinancialReport.aspx) — noted as follow-ups, not merged. Publish deferred to AFTER the babysit's sync (its CI checkout predates this and would revert prod to frozen pmayg).

### 2026-08-05 01:10 — Discovery agents (PMAY-G finance + MGNREGA social audit): initial inconclusive read
**Agent:** Claude Code (+ pmayg-recon2, socialaudit-recon2 subagents)
**Status:** ⏸️ superseded above for PMAY-G; social-audit dead-end stands
**Files:** `DATA_CLAIMS.md` (dated notes on CLAIM-0016 + CLAIM-0001)

HANDOFF follow-up #1. Dispatched two read-only discovery agents to hunt for un-gated routes for the two frozen sources (PMAY-G finance behind a captcha; MGNREGA social-audit misappropriation/issues). BOTH pairs hung on the slow government portals despite explicit per-request timeout instructions — the same failure mode Sam flagged mid-session ("reboot the agents that are stuck"); rebooted once, the second pair hung too and was stopped after 30+ min unresponsive. Outcome: INCONCLUSIVE, not a fresh confirmed dead-end. The prior session's thorough documented dead-ends stand (findings.md 83-89 for social audit; captcha B.3 for PMAY-G finance). Recorded honestly as dated notes on CLAIM-0016 + CLAIM-0001 (no un-gated route confirmed; freezes stand; re-sourcing open). LESSON for re-runs: these portals hang agents — give any retry hard per-call timeouts (curl --max-time) AND a strict token/turn budget, or probe the specific hidden-handler URLs directly instead of via an open-ended agent.

### 2026-08-04 00:35 — March-audit defect sweep: verified all vs current code
**Agent:** Claude Code (+ defect-verifier subagent cross-check)
**Status:** ✅ done
**Files:** (verification only — no functional survivors to fix)

Closed HANDOFF follow-up #5. Verified every defect from findings.md's 2026-08-04 frontend/Python/pipeline audit against current code. **ALL functional defects were already fixed in the overhaul:** F1 resolveState now queries district_scores (every district, not 3 tables); F1b action page links carry `?state=`; F2 district page money_flow filters by state (explicit 14-duplicate-names comment); F3 mp/constituency routes no longer recompute any formula (the 60/40 duplication is gone); F4 get-base-url.ts DELETED (no self-fetch); F5 broken NSAP diagnosis (beneficiaries_eligible>0 gate) removed, replaced by an honest data-quality caveat; F6 scheme slugs resolved via resolveSchemeParam/VALID_SCHEME_SLUGS (pds-nfsa reachable); F7 recovery-rate prints `%` correctly; F8 embed.js DELETED; F9 /api/v1/query is an honest stub (parked llm), constituency/search has LIMIT 25, stats uses force-dynamic + Promise.all (not 42 serial), read-heavy routes set revalidate; F10 types.ts 14→3 exports (all used by IndiaMap); P1 run_all uses importlib; P2 freshness covers all 11 schemes (TS + Python); P5 CI builds the DB (run_all --load-only) + runs ruff + py3.14 matching pyproject. **Deliberately PARKED (intentional):** /api/v1/query stub (llm parked), /trends (FastAPI api/ is local-only, not deployed), pg_adapter/pg_schema (env-gated optional Postgres path, lazy-imported by connection.py — not dead). **Cosmetic (left):** .gitignore lists hisaab.db twice (harmless); tasks.md gitignored (intentional — trio is local working memory). **New gap found (not on the list):** pin_constituency has a curated `_latest.json` (19,169 rows) but no wired loader — loaded manually this session; the new sync_turso empty-table guard protects prod; wiring a proper loader is a handoff follow-up.

### 2026-08-05 — pin_constituency loader wired into --load-only (handoff follow-up #1)
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `db/loaders.py`, `db/__init__.py`, `tests/test_loaders.py`, `data/curated/pin_constituency_all_latest.json` (renamed from pin_constituency_latest.json), `CLAUDE.md`

Closed the gap where the curated PIN→constituency file (19,169 rows, DERIVED-2026-0002) had no loader — the table was kept alive only by the manual load + sync_turso wipe-guard. Added `load_pin_constituency` to the LOADERS registry (validates 6-digit PINs, keeps constituency names verbatim for the PC-name join, ignores fin_year — mapping is not year-scoped) and renamed the curated file to `pin_constituency_all_latest.json` so run_all's existing `{loader}_*_latest.json` glob picks it up with zero special-casing. A fresh CI DB now rebuilds the table from git. Verified: --load-only round-trips all 19,169 rows byte-identical to the manual load; district_scores unchanged except computed_at; 515 pytest green (4 new tests incl. a glob-match regression guard), ruff + tsc + lint + credential-free build clean.

### 2026-08-05 — MGNREGA social-audit un-gated route re-hunt: conclusive dead-end
**Agent:** Claude Code (direct curl probes, no subagents)
**Status:** ✅ done (dead-end recorded)
**Files:** `DATA_CLAIMS.md` (CLAIM-2026-0001 dated note), `findings.md`

Re-hunted per handoff #4 using ~15 direct probes with hard 20-30s timeouts (the recorded lesson: these portals hang open-ended agents). Result: the captcha gate MOVED but did not lift — MISreport4.aspx relocated from mnregaweb2 to mnregaweb4.dord.gov.in (both /netnrega/ and /netnregarep/ copies, txtCaptcha/hfCaptcha intact), the two SA report pages 302 to error.html without a Digest on both mirrors, the citizen page's new SocialAuditFindings link points at TCP-dead mnregaweb2.nic.in, and the Digest-leaking statepage pgr zone is grievance-only. misappropriation/issues_reported stay frozen at FY2024-25. Recorded (not built): a human could solve the captcha once per FY and harvest replayable signed URLs.

### 2026-08-05 — PIN→representative integrity: 387 impossible rows dropped, reserved-seat + vintage-state lookups fixed
**Agent:** Claude Code
**Status:** ✅ done (commit queued behind the in-flight refresh run)
**Files:** `scripts/clean_pin_constituency.py` (new), `data/curated/pin_constituency_all_latest.json` (19,169→18,782), `db/normalize_states.py` (UTTARKHAND variant), `web/src/lib/vintage-states.ts` (new), `web/src/app/api/v1/pin/[pin_code]/route.ts`, `web/src/lib/action-brief.ts`, `tests/test_pin_constituency_clean.py`, `DATA_CLAIMS.md` (DERIVED-2026-0002 correction)

Found while verifying the loader: prod served PIN 823001 (GAYAJI/BIHAR) with constituency KARIMGANJ/ASSAM and that MP as "precise" — the March spatial join put 387 PINs in another state's constituency (electorally impossible; PCs never cross state lines). Cleaner drops them (fallback to honest district-level list); vintage families KEPT (AP↔Telangana 2014, JK↔Ladakh 2019 — internally consistent labels; 242 directory-absent PINs). Then two route-layer diseases: (1) MP lookup was name-only — AURANGABAD-class name reuse served the wrong state's MP (now state-scoped with vintage equivalence; the 3 UNIQUE-constraint-orphaned seats return honest null pending the mp_info migration); (2) exact-name matching missed every reserved seat — datameet carries " (SC)/(ST)" (250 PCs, 953 ACs), OpenCity/MyNeta drop it. Suffix-stripped matching: MP coverage 386→481/532 PC rows, MLA 2,717→3,642/4,020 AC rows, Telangana MLAs resolve for the first time. All gates green (524 pytest).

### 2026-08-05 — Refresh babysit rounds 1-3: pipeline validated in CI, publish bug root-caused and fixed, prod current
**Agent:** Claude Code
**Status:** ✅ done (round 3 = final CI proof, running at entry time)
**Files:** `scripts/sync_turso.py` (retries 4→8, retry log names statement, index drop+create), `.github/workflows/refresh-data.yml` (commit-before-publish + pull --rebase), `findings.md`, `learnings.md` (2 postmortems)

Dispatched the Sunday-default refresh three times as the dress rehearsal. ROUND 1 (46m, failed at publish): verify_refresh clean over 460 files IN CI; wipe-guard KEPT 4 empty civic tables; MGNREGA targeted FY2025-2026 correctly; found ALL *.dord.gov.in portals 401 GitHub-runner IPs (MGNREGA 36/36 states, PMGSY, PMAY-G B.3 — those 3 schemes can only refresh from a residential IP; fail-fast + guards keep last-good honestly); publish died on the libsql KeyError with prod tables pushed but the data commit skipped. ROUND 2 (with retries 4→8 + commit-before-publish): data commit landed FIRST (03539eb, 77 files — JJM/NFSA/NSAP-fin/POSHAN-fin/SBM/UDISE+ refreshed from CI), publish failed AGAIN at the now-NAMED statement `CREATE INDEX idx_ac_district` — 7/7 retries, proving it deterministic: wipe-guard-KEPT tables retain their old indexes and sqlite_master strips IF NOT EXISTS from replayed DDL. Fixed: indexes drop+create in one batch like views (707bd7e). Validated the fix by publishing locally against real Turso: 34 tables / 62,709 rows verified, index phase green, prod now serves the pulled CI-fresh data + the cleaned pin_constituency. Prod verified: 823001 → GAYAJI precise:false, GAYA (SC) → JITAN RAM MANJHI (Karimganj/Assam lie gone), 10/10 MLAs; 500003 → Secunderabad + G. Kishan Reddy + 7/7 Telangana MLAs (first time); smoke 5/5 incl. /action/823001. Round 3 dispatched as the end-to-end green proof for Sunday.

### 2026-08-05 — Session close-out: round 3 fully green, prod verified, handoff written
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `HANDOFF.md` (rewritten), trio

Round 3 (30987314636) = the definitive proof: scrape → verify gate → load → commit-before-publish (e51a847, 76 files) → publish (41 indexes/views pushed in CI for the first time, 34 tables / 52,169 rows verified, all 5 empty civic tables KEPT by the guard) → smoke, ALL GREEN. Sunday's cron runs this exact path. Prod final check: 823001 precise:false + GAYA (SC) → JITAN RAM MANJHI, smoke 3/3. Local DB rebuilt from pulled canon (pin_constituency 18,782). All four handoff items closed or handed off: loader DONE, babysit DONE (3 rounds, 2 root-caused fixes), key BLOCKED on Sam (still unregistered), social-audit DEAD-END recorded. Bonus: the PIN-integrity defect found and fixed end-to-end. Zero agents spawned; nothing to TaskStop.

### 2026-08-05 13:20 — PC-name registry: every mapped constituency resolves its MP; 5 UT seats seeded
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `constituency/pc_name_registry.py` (new), `constituency/{mapper,ingest,seed_data}.py`, `db/loaders.py`, `scripts/gen_pc_name_registry.py` (new), `web/src/lib/{pc-name-registry.ts (generated),vintage-states.ts}`, `web/src/app/api/v1/{mp,constituency}/[name]/route.ts`, `api/routes/constituency.py`, `data/curated/pin_constituency_all_latest.json` (−1 row), `tests/test_pc_name_registry.py` (22 tests), `DATA_CLAIMS.md` (0036, 0037 + notes on 0035/DERIVED-0002), `CLAUDE.md`

Closed handoff item 3 (+UT bonus). Curated 41 state-scoped PC-name variants → official 2024 seat names, each verified against the 2024 winner (Wikipedia 18th-LS list + state result pages cross-checked against mp_info): datameet truncations/mojibake/pre-delimitation names AND 17 OpenCity-side typos (the wart set was two-sided — KURNOOLU, BAHARAICH, PATLIPUTRA, JOYNAGAR…). Registry applied at every label-WRITING boundary (cd/ac/mp ingest + pin_constituency loader; curated file stays source-faithful), so stored labels are canonical and joins stay mechanical; user-supplied legacy names expand via pc_name_lookup_candidates ↔ pcNameLookupCandidates (TS twin generated, pytest drift guard). Civic ingest is wholesale-replace now (renamed keys orphaned old rows under INSERT OR REPLACE — same class the MLA ingest guarded). Also: 5 non-assembly UT seats seeded into cd (8 rows, PIN-directory-grounded; Delhi's 7 left as a recorded structural gap), 1 electorally-impossible pin row dropped (583211), stale "MAHOBA *" handoff wart confirmed nonexistent. Acceptance: 537/537 cd rows find their MP (was 498/532), mp orphans = exactly Delhi 7, district_scores byte-identical (1,888 rows). Gates: 557 pytest, ruff, tsc, lint, build, verify_refresh, gen --check all green. Published (34 tables / 62,719 rows) + prod smoke: KALIABOR→KAZIRANGA/Tasa, PONDICHERRY→PUDUCHERRY/Vaithilingam, HARDWAR→HARIDWAR/Rawat, CHANDIGARH & DAMAN & DIU report cards live, 823001/824111/174305/AURANGABAD-300 regressions green. CI green (5617482).

### 2026-08-05 19:35 — "Use my location": pin_geo centroids + POST /api/v1/locate + PinEntry flow
**Agent:** Claude Code (Fable, inline — two Opus dispatches died on API 529s; recon by Haiku agent, web-layer memo agent pending)
**Status:** ✅ done (publish + prod smoke in the following entry)
**Files:** `scripts/build_pin_geo.py` (new), `db/schema.py` (pin_geo + idx), `db/loaders.py` (+load_pin_geo), `db/__init__.py`, `data/curated/pin_geo_all_latest.json` (new, 19,238 PINs), `tests/test_pin_geo.py` (new, 7 tests), `web/src/app/api/v1/locate/route.ts` (new), `web/src/components/PinEntry.tsx`, `DATA_CLAIMS.md` (CLAIM-2026-0038), `CLAUDE.md`

Mobile geolocation entry for the hero flow (Sam's ship-push directive). GeoNames IN.zip (155,570 locality rows, CC BY 4.0) → median-centroid per distinct PIN with spread_km quality signal; 97.9% coverage of the served directory; loader validates 6-digit + India bbox; builder refuses coverage reduction and writes atomically. POST /api/v1/locate: expanding bbox prefilter + haversine, falls through directory-absent GeoNames pins, returns pin+district+state+distance; coords POST-body-only (never in request logs), transient, no-store — privacy contract in the claim + route comment. PinEntry: gesture-triggered getCurrentPosition (highAccuracy off, 10s timeout), confirm-before-navigate match card ("PIN X · district, ~Y km — see what's owed / not my area"), honest per-error-code fallback copy, GeoNames attribution in-card, aria-live/aria-busy. Scores byte-identical (1,888); 564 pytest + ruff + tsc + lint + build green.

### 2026-08-05 19:50 — Location feature live on prod; session close-out
**Agent:** Claude Code
**Status:** ✅ done
**Files:** prod (35 tables / 81,957 rows), `HANDOFF.md` (rewritten), trio

Synced pin_geo to Turso (+19,238 rows exactly), Vercel deployed ae2d001, prod smoke: Connaught Place → 110055/DELHI 1.2km; inside-Kaziranga-park point → 782136/KARBI ANGLONG 16km (honest sparse-area distance); Gaya → 823002/GAYAJI 6.5km; London → 404; garbage body → 400. Coordinate privacy verified by design (POST body, no-store, no logging). Agent ledger: geo-recon (Haiku, delivered + stopped), geo-research + pin-geo-builder (Opus, both died on API 529s, stopped), geo-research2 (Opus, completed but never delivered its memo despite a ping — stopped; its four questions were resolved inline and shipped). Orchestration standard pinned to ~/.claude/references/model-routing.md §Role routing standard + project memory. Zero leaked agents at close.

### 2026-08-06 09:55 — Ship-polish sweep: hero hydration, deferred map, honest view percentages, Delhi MP gap
**Agent:** Claude Code (teammate, polish-spec A1–F1)
**Status:** ✅ done (uncommitted — orchestrator reviews)
**Files:** `db/schema.py`, `action_brief/{engine,diagnosis,models}.py`, `tests/{test_cross_scheme,test_action_brief}.py`, `web/src/lib/{format-place.ts (new),action-brief.ts,action-types.ts}`, `web/src/components/{PinEntry,IndiaMap,DiagnosisCard (new),SectionHeader (new)}.tsx`, `web/src/app/{action/[pin],district/[name]}/page.tsx`

PinEntry: mount-flag kills the geolocation hydration mismatch, meta/ctrl/alt chords no longer swallowed (paste was broken), autoFocus now `(pointer: fine)`-only, focus follows the match card. IndiaMap defers its 778KB topojson + scores fetch behind an IntersectionObserver and computes the disputed-feature count instead of hardcoding 28. Views stopped fabricating percentages: every `ELSE 0` utilization branch → `ELSE NULL` (7 schemes, 3,479 rows), NFSA district offtake → NULL (744 rows, all zero at source), NSAP district GROUP BY collapses 3 pension sub-schemes into the district total (WEST/DELHI: 544 → 16,986 pensioners). district_scores byte-identical, 1,888 rows — composite only reads `utilization_pct > 0`, so the change is score-invariant by construction. Delhi action pages now resolve their MP via the pin_constituency fallback (110018 → KAMALJEET SEHRAWAT), and `schemes_checked` replaces the green "no issues" all-clear with an honest "nothing reports district data here" box. 571 pytest (+7) + ruff + tsc + lint + build green.

### 2026-08-06 10:20 — Addendum E5 + G1: unknown-PIN dead-end, locate null-coercion
**Agent:** Claude Code (teammate)
**Status:** ✅ done (uncommitted)
**Files:** `web/src/app/action/[pin]/page.tsx`, `web/src/components/PinNotice.tsx` (new), `web/src/app/api/v1/locate/route.ts`

E5: /action/999999 no longer falls through to notFound() and the generic "does not exist or has been moved" shell — a well-formed PIN we don't serve now gets "PIN 999999 not found" plus retype guidance. Both dead-end states (bad format, unknown PIN) share the new PinNotice component; the invalid-format copy is byte-identical to before. E1's generateMetadata already returns `PIN {pin}` for this case, so the tab title is honest too. G1: /api/v1/locate validated with `Number(body?.lat)`, and Number(null)/Number("")/Number([]) are all 0 — a "valid" coordinate that reached the bounds check and returned 404 "outside India" for what was really malformed input. Now a `typeof === "number"` gate runs before any coercion, returning the existing 400. No logging, no header changes (CLAIM-2026-0038 intact). Side effect: string coordinates ("28.6") are now a 400 rather than being coerced — PinEntry sends real numbers, but it is a breaking strictness increase for any external caller.

### 2026-08-06 10:05 — Ship-polish audit: forensics + spec (orchestrator half of the unit above)
**Agent:** Claude Code (Fable, orchestrator)
**Status:** ✅ done
**Files:** `findings.md` (4 entries), scratchpad polish-spec.md, screenshots

Phone-viewport Playwright pass over home → locate → action → district reproduced every handoff rough edge and found five more: PinEntry hydration mismatch (navigator read in render — React 19 regenerated the tree every load), Cmd/Ctrl+V paste dead (keydown digit-gate), focus dropped to body when the locate button unmounted, unknown-PIN 404 shell, locate null-coercion. DB forensics: money_flow/scheme_finance fabricated 0% via ELSE 0 (3,479 rows / 7 schemes; NFSA offtake_pct zero for all 744 district rows; PM Kisan 821/1,073 rows without registered counts); NSAP served 3 indistinguishable sub-scheme rows (718 district-years). Score-safety proven BEFORE fixing: composite.py filters utilization_pct > 0 / delivery_pct > 0, so fabricated zeros never scored — the whole fix set is score-invariant. Topojson scare killed: Vercel serves it brotli at 778KB with ETag 304s (not 2.3MB). Both auditor dispatches (accessibility-auditor, code-reviewer) truncated to silence twice — stopped, postmortem in learnings.md, re-covered inline + one scoped general-purpose pass.

### 2026-08-06 10:35 — Ship-polish REVIEWED and LIVE: f0fdce5 published + deployed + smoke-green
**Agent:** Claude Code (Fable review; Opus implemented)
**Status:** ✅ done
**Files:** commit `f0fdce5` (18 files), prod Turso (35 tables / 81,957 rows), Vercel deploy

Line-by-line review of the Opus diff: views exact to spec (10 ELSE NULL sites, NSAP GROUP BY with NULLIF target, MAX(source_url)), twins in lockstep, privacy contract untouched. Independently re-proved score-invariance (md5 of district_scores incl. schemes_with_data identical between the pre-change DB backup and the rebuilt DB: 9b844d0f…). Fixed two things the implementer missed, found via live verification: nested `<main>` landmarks (layout + 4 child pages — layout now owns the single landmark) and the IntersectionObserver rootMargin 300px that could never defer given the ~600px hero (now 0px; verified deferring at 560px viewport and firing on scroll). Full gates re-run post-changes: 571 pytest (+7), ruff, tsc, eslint, build. Playwright re-verification: hydration error gone, match card "PIN 110018 · West Delhi", focus lands on the CTA, null body → 400, Delhi action page neutral + MP via pin_constituency, Gayaji unchanged-healthy. Committed BEFORE publish; sync_turso 35/35 tables verified; prod smoke: locate 3.3km, action/110018 MP present + schemes_checked [], WEST/DELHI NSAP one row 16,986 pensioners ₹466.8L, PM Kisan util null, all pages 200. Dev-server note: running `next build` while `next dev` serves the same .next corrupts the dev server — rebuilt clean.

### 2026-08-06 10:40 — DATA_GOV_IN_API_KEY registered account-wide; pmkisan back on weekly; schemes=all dispatched
**Agent:** Claude Code
**Status:** ✅ done (refresh run 31071577044 in progress — babysit result pending)
**Files:** GH secret store, `.github/workflows/refresh-data.yml` (commit `11f0ea8`)

Sam supplied the data.gov.in key mid-session unsure whether it was per-dataset. Proven account-wide by probing three resources across three ministries (PM Kisan village 12.95M rows, JJM allocation, NSAP IGNOAPS) — all status ok. Registered via gh secret set (Scepter yes in-conversation; key lives only in GitHub's store, never in any file). Restored pmkisan to the weekly default (both the dispatch input and the schedule fallback now 'all') — the e19f780 removal was purely the demo-key throttle. Dispatched schemes=all AFTER the polish publish so CI's checkout carries the new views (revert-race lesson from the PMAY-G session applied).

### 2026-08-06 10:55 — WCAG 2.2 AA pass applied: computed-contrast fixes live (f6d39d1)
**Agent:** Claude Code (Fable applied; general-purpose Opus agent audited)
**Status:** ✅ done
**Files:** `web/src/app/globals.css`, `web/src/components/{PinEntry,IndiaMap,SchemeRow,DiagnosisCard}.tsx`

### 2026-08-06 11:55 — Complaint layer LIVE: why / how / whom to complain, per district (fd86da2)
**Agent:** Claude Code (Fable inline; Opus research agent for source compilation)
**Status:** ✅ done
**Files:** `db/schema.py` (scheme_entitlements + grievance_channels.authority), `db/loaders.py` (2 loaders, filter-before-clear), `data/curated/{grievance_channels,scheme_entitlements}_all_latest.json` (NEW, tracked), `action_brief/{engine,models}.py`, `web/src/lib/{action-brief,action-types}.ts`, `web/src/components/ComplaintKit.tsx` (new), action page, `tests/test_action_brief.py`, `DATA_CLAIMS.md` (0039/0040), `CLAUDE.md`

Sam's directive (the manifesto vignettes "aren't enough"): the action page now carries per-scheme complaint kits — WHAT YOU ARE OWED (legal entitlement + act/section: MGNREGA 15-day wages + 0.05%/day compensation verified inside the cited India Code schedule PDF; NFSA s.8 food-security allowance; NSAP central-share framing), COMPLAIN WHEN (concrete triggers incl. the e-PoS-failed case), and WHERE TO TAKE IT (52 verified rungs, local→national, only officially-printed phones — PM Kisan's folk-memory helplines deliberately absent because pmkisan.gov.in doesn't print them). Kits render for every scheme PRESENT in the district, flagged-first — decoupled from shortfall gating because a personal grievance doesn't wait for a district aggregate. Universal block: CPGRAMS (registration friction stated), RTI, Sansad + the citizen's named MP/MLA. Research: Opus agent compiled from official sources; I re-verified 44/44 URLs (all 200) and the key legal figure before curating. Also resolved: the March grievance_channels orphan (rows lived only in prod, never git, stale nic.in URLs) is wholesale-replaced by tracked curated data. Twins in lockstep; legacy hardcoded actions retired behind a data-presence fallback. Prod: 36 tables / 82,020 rows, /action/632001 serves 10 kits + S Jagathratchakan (MP) + Vilwanathan (MLA); phone screenshot verified.

### 2026-08-06 13:05 — Session close-out: HANDOFF.md rewritten for Codex, root AGENTS.md entry point (0162070)
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `HANDOFF.md` (rewritten, incl. paste-ready Codex prompt), `AGENTS.md` (new, committed), trio

Handoff written tool-agnostic for Codex: state (7 commits today: f0fdce5 polish, f6d39d1 WCAG, 11f0ea8 key+pmkisan, ae52701 CI refresh, ddffe8d docs/cleanup, fd86da2 complaint layer, 57feea9 unification), prioritized follow-ups (Monday cron check, district folds w/ recorded procedure, NSAP worst-route verify, RTE-kit decision, MANIFESTO vignette refresh), the full constraint list, verification commands. Root AGENTS.md added (Codex reads that convention natively) routing any agent through CLAUDE.md → ONBOARDING → HANDOFF → trio. Prod verified 3/3 before writing "green": home/action/district all 200, grievance tables 52+11 rows local=prod. Agent ledger for the day: 6 spawned (a11y-hero + review-locate died silent (turn-cap postmortem in learnings), polish-impl delivered via diff, a11y-final + grievance-research delivered reports, all TaskStopped on receipt); zero leaks at close.

### 2026-08-06 12:40 — Entry-point unification: map clicks and PIN entry net the same brief (57feea9)
**Agent:** Claude Code (Fable inline — design + implementation)
**Status:** ✅ done
**Files:** `web/src/app/district/[name]/page.tsx` (rewritten as the district-grain brief), `web/src/app/action/[pin]/page.tsx` (+Scheme Data section), `web/src/lib/{action-brief.ts,money-flow.ts (new),format-place.ts}`, `web/src/components/SchemeDataSection.tsx` (new), `action_brief/{engine,models}.py` (build_district_brief twin), `tests/test_action_brief.py`

Sam flagged that searching a PIN vs clicking the map produced different products ("one has actions and one doesn't") — an accident of history, not design (the district page predates the action engine). Brainstormed three options; rejected the arbitrary-PIN redirect (would present one constituency's MP as "yours" to a whole district — precision-dishonesty). Shipped "one brief, two lenses": the district page now carries the same four sections as the PIN page (representatives / Issues Found / How to Complain / Scheme Data), with honestly-PLURAL MPs — every Lok Sabha seat overlapping the district, e.g. Gayaji lists Aurangabad+Gaya+Jahanabad MPs — plus a "10 assembly seats cover this district — enter your PIN for your exact MP and MLA" nudge. The PIN page gains the scheme evidence cards it lacked. Twins in lockstep (build_district_brief mirrors buildDistrictBrief; +1 test asserting section parity and plural MPs). Prod verified both paths on phone viewport: district/gayaji shows 3 MPs + 1 issue + 10 kits + 9 scheme cards; action/823001 shows all four sections with the single precise MP. 573 pytest + ruff + tsc + eslint + build green.

### 2026-08-06 11:10 — WCAG batch context (see entry above)
**Agent:** Claude Code
**Status:** ✅ done (detail in the 10:55 entry)

The scoped re-cover agent (general-purpose, after both specialized auditors truncated to silence) delivered a fully computed contrast audit — every ratio calculated OKLCH→WCAG, methodology validated against a known anchor. Applied all of it: --text-muted 3.38→4.5:1+ (one token, 10 files repo-wide), focus ring 2.01→3.4:1, PinEntry input/button boundary was 1.18:1 (no perceivable edge — now #84849a), placeholder 1.91→5.19:1, tooltip score line got a darker BAND_TEXT ramp (fills untouched — choropleth ranges are the 1.4.11 essential exception), badge constants darkened under white 11px text, Esc dismisses the map tooltip, svg alt text now score-bearing + sr-only text-route pointer, 820 inert per-path aria-labels deleted. Its sharpest catch: the match card sat inside an aria-live region while we programmatically focus its CTA — the polite queue and focus event race and garble screen readers; live region now wraps only the error line. Verdicts it PASSED and I accepted with its reasoning: touch targets (24px floor met; map paths are the 2.5.8 essential exception), role=img prunes path children (adding aria-hidden ×820 buys nothing), progress bars honest via adjacent text (adding role=progressbar would double-announce), reduced-motion fully covered incl. the inline transition beaten by the !important longhand. Deferred: SourceLink 16px height (out of scope, clears via spacing exception today). Gates green; visual screenshots hold; pushed f6d39d1 → Vercel.

### 2026-08-06 13:16 — Human-use UI diagnosis and system-level redesign brief
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/page.tsx`, `web/src/app/action/[pin]/page.tsx`, `web/src/app/district/[name]/page.tsx`, `web/src/components/ComplaintKit.tsx`, `web/src/app/globals.css`

Audited the three public pages and the live Gayaji flow after Sam made humane use and UI the priority. The current product is data-first rather than task-first: a person sees scheme acronyms and up to 47 grievance rungs before a clear next action; the proposed redesign makes PIN entry, the first actionable shortfall, plain-language scheme names, and progressive disclosure the shared hierarchy across both brief routes.

### 2026-08-06 13:50 — Human-first brief UI shipped through full local gates
**Agent:** Codex
**Status:** ✅ done
**Files:** `design.md`, `.hallmark/`, `web/src/app/{page,layout,error,not-found}.tsx`, `web/src/app/{tokens,base,forms,map,brief,complaints,evidence}.css`, `web/src/app/{action/[pin],district/[name]}/page.tsx`, `web/src/components/{BriefOverview,ComplaintKit,DiagnosisCard,IndiaMap,IndiaMapParts,PinEntry,PinNotice,SchemeDataSection,SchemeRow,SectionHeader,SourceLink}.tsx`, `web/src/lib/scheme-display.ts`

Rewired the existing three-page product without adding routes: PIN is the primary task, PIN and district entries now share one action-first brief, rights use human need labels, the local complaint rung is visible before escalation, evidence is collapsed but complete, and the map has a native district picker. No data, API, formula, route-tree, or claim-registry changes; 573 pytest + ruff + TypeScript + ESLint + production build passed, and local home/action/district smoke returned HTTP 200.

### 2026-08-06 13:55 — NSAP worst-route tripling audit
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/api/v1/scheme/[scheme]/worst/route.ts`

Verified the live `GET /api/v1/scheme/nsap/worst?state=BIHAR` path returns the intentional HTTP 422 honesty guard. It neither reads `nsap_district` nor returns a repeated ranking, because beneficiary counts without an eligibility target cannot honestly define “worst”; no fix was required.

### 2026-08-06 13:56 — Human-first UI published to production
**Agent:** Codex
**Status:** ✅ done
**Files:** `c7e6509`

Published in the required order: gates → commit → Turso sync → push → smoke. Turso verified 36 tables / 82,020 rows with the empty-local `metrics_snapshot` protection holding 13,957 remote rows; Vercel deployment `dpl_5YCwH4x4PBcnmYRN2r4mAGLGv4Lf` reached Ready and aliased to `hisaab-one.vercel.app`; home, PIN 823001, Gayaji district, locate, and the production stylesheet all returned HTTP 200 with the new humane-flow copy present.

### 2026-08-06 15:57 — Replaced three page identities with one anti-slop task surface
**Agent:** Codex
**Status:** ✅ done
**Files:** `design.md`, `.hallmark/`, `CLAUDE.md`, `web/next.config.ts`, `web/src/app/{page,layout,loading}.tsx`, `web/src/app/{tokens,base,forms,surface,evidence}.css`, `web/src/app/{action/[pin],district/[name]}/page.tsx`, `web/src/app/api/v1/districts/route.ts`, `web/src/components/{AccountabilityResult,ComplaintGuide,DistrictPicker,PinEntry,SchemeDataSection,SchemeRow,SourceLink}.tsx`

Sam rejected the prior three-page polish as “literal trash,” so the product architecture changed rather than receiving another skin. `/` now owns lookup, PIN results, and district results; old action/district URLs are real 308 compatibility redirects; Aptos-first austere UI removes the map, oversized editorial styling, stat strips, repeated complaint cards, and surprise sixth-digit navigation. All complaint/evidence coverage remains reachable through one problem selector and disclosures. Local gates passed: 573 pytest + ruff + TypeScript + ESLint + production build; lookup, result, invalid-input, redirects, locate, and 944 state-scoped district items smoked green.

### 2026-08-06 16:04 — Published the single-surface anti-slop interface
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/page.tsx`, `web/src/components/AccountabilityResult.tsx`, `web/src/components/ComplaintGuide.tsx`, `web/src/app/surface.css`, `web/next.config.ts`

Committed `8d5be15`, verified the 36-table / 82,020-row Turso sync, pushed `main`, and smoked the Ready production deployment `dpl_2WB6wNCXTW4zfbWtgaot69eue18R` at `hisaab-one.vercel.app`. The only UI page is now `/`; former PIN and district pages return compatibility 308 redirects into that surface.

### 2026-08-06 16:24 — Removed misleading representative and scheme evidence
**Agent:** Codex
**Status:** ✅ done
**Files:** `db/schema.py`, `tests/test_cross_scheme.py`, `web/src/app/page.tsx`, `web/src/components/AccountabilityResult.tsx`, `web/src/components/SchemeRow.tsx`, `DATA_CLAIMS.md`

A research audit caught two live tenet violations: a district fallback presented as an exact MP/MLA, and generic evidence UI presenting PM POSHAN's daily snapshot as a delivery/fund percentage plus unavailable district money as ₹0. Commit `512562b` now shows plural overlapping MPs with an explicit precision limit, converts placeholder money to NULL, preserves the exact PM POSHAN daily count without a target/percentage, and is production-smoked on deployment `dpl_47rvdzyzzipwHbDx6SoH54HszZH5`; 574 tests, Ruff, TypeScript, ESLint, and Next build passed.

### 2026-08-06 16:31 — Defined the citizen-first Hisaab service
**Agent:** Codex
**Status:** ✅ done
**Files:** `design.md`, `SERVICE_DESIGN.md`, `USER_RESEARCH_PLAN.md`, `.hallmark/log.json`

Completed a three-stream repository, citizen-access, and service-design research pass and converted it into a Double Diamond service direction. Hisaab is now specified as one staged public-service casework utility—problem to named action, preparation, and escalation—with aggregate evidence and representatives demoted to supporting context; the issue-first sequence remains an explicit hypothesis until direct citizen research validates it.

### 2026-08-06 16:34 — Published the citizen service-design record
**Agent:** Codex
**Status:** ✅ done
**Files:** `design.md`, `SERVICE_DESIGN.md`, `USER_RESEARCH_PLAN.md`, `.hallmark/log.json`

Committed and pushed `c2822e6` to `main`. The automatic production deployment `dpl_2uxDYXo9GJuEWgo4xcW3rbPDYjxt` reached Ready at `hisaab-one.vercel.app`; root copy, PIN privacy wording, independent status, and the schemes API passed smoke checks. This documentation-only deployment did not change or re-sync Turso data.

### 2026-08-06 17:51 — Decoupled complaint rights from district data
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/lib/action-brief.ts`, `web/src/lib/action-types.ts`, `action_brief/engine.py`, `action_brief/models.py`, `tests/test_action_brief.py`

Both action-brief twins now build complaint kits from the complete curated entitlement and route registries rather than local `scheme_delivery`/`money_flow` presence. RTE remains available with no district education row, route and entitlement verification provenance survives the API contract, and legacy TypeScript action steps are now derived from sourced registry destinations; the focused Python suite and TypeScript compile passed.

### 2026-08-06 17:58 — Removed stale and misleading action paths
**Agent:** Codex
**Status:** ✅ done
**Files:** `action_brief/diagnosis.py`, `action_brief/actions.py`, `action_brief/card.py`, `action_brief/models.py`, `directory/seed_data.py`, `tests/test_action_brief.py`, `tests/test_directory.py`

The Python brief no longer diagnoses PM POSHAN's daily snapshot, NFSA's unpublished district offtake, or NSAP's non-eligibility denominator; the legacy action contract no longer invents a universal 30-day CPGRAMS rule. The seeder now reads the tracked 52-route registry instead of restoring forbidden phones, and SVG cards no longer present an arbitrary district MLA/MP as personal. Forty-two focused tests passed.

### 2026-08-06 18:20 — Built the issue-first citizen service shell
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/page.tsx`, `web/src/components/ServiceStart.tsx`, `web/src/components/ComplaintGuide.tsx`, `web/src/components/PinEntry.tsx`, `web/src/components/DistrictPicker.tsx`, `web/src/components/AccountabilityResult.tsx`, `web/src/app/{base,forms,surface,tokens,evidence}.css`

Replaced the lookup/result chooser with a server-rendered problem → situation → area flow, then put one sourced action plan before optional area evidence and representatives. URL state preserves back/refresh/share, explicit submit replaces surprise navigation, the coordinate privacy notice precedes permission, and copy/print/share controls never collect personal case data.

### 2026-08-06 18:35 — Closed the humane-service acceptance blockers
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/page.tsx`, `web/src/components/{GeneralResult,ServiceStart,PinEntry,ComplaintGuide}.tsx`, `web/src/lib/action-brief.ts`, `web/src/app/{base,surface}.css`

The release audit now passes: scheme routes are equal-weight rather than falsely trigger-matched, the preparation artifact is a neutral usable case outline, PIN works as a native GET, district entry has a no-JS fallback, general complaints skip irrelevant area collection, headings are coherent, printing stays concise, and libSQL rows cross the client boundary as plain objects. TypeScript, ESLint, production build, and the final rendered-flow smoke passed.

### 2026-08-06 18:38 — Published the citizen-first complaint service
**Agent:** Codex
**Status:** ✅ done
**Files:** `de12950`, `web/src/app/page.tsx`, `web/src/components/ServiceStart.tsx`, `web/src/components/ComplaintGuide.tsx`

Published in the required order: final gates → commit `de12950` → Turso sync → push → production smoke. Turso verified 36 tables / 82,020 local rows while preserving 13,957 remote-only snapshots; Vercel deployment `dpl_9Gw2YMLXRXZ6EoiapPcmcEq2itk5` reached Ready, and production passed the staged flow, general no-area path, RTE result, 11/45/7 route API, 945 state-scoped district registry, empty runtime diagnosis, and both compatibility redirects.

### 2026-08-06 19:51 — Re-centered the product thesis after Sam's critique
**Agent:** Codex
**Status:** ✅ done
**Files:** `MANIFESTO.md`, `README.md`, `design.md`

Re-read the canonical product record and identified the conceptual inversion: the shipped interface made complaint navigation primary even though Hisaab exists to answer “Where did the money go?” with a sourced local public account. The next design pass must be area → account → evidence/accountability → contextual action, while retaining the complaint registry as a secondary capability.

### 2026-08-06 20:37 — Locked the area-first public-account contract
**Agent:** Codex
**Status:** ✅ done
**Files:** `design.md`, `README.md`, `SERVICE_DESIGN.md`

Re-centered Hisaab on area → exact public record → coverage limits → contextual action. The complaint casework model is retained as a secondary layer, while unsupported MP-promise copy and complaint-first product framing are retired.

### 2026-08-07 00:24 — Preserve NFSA record dates
**Agent:** Codex
**Status:** ✅ done
**Files:** `db/schema.py`, `db/connection.py`, `db/loaders.py`, `tests/test_loaders.py`, `web/src/lib/area-account.ts`

Added an idempotent schema upgrade and nullable loader field for NFSA's already-curated per-row reporting date, rebuilt without deleting the database, and verified all 744 NFSA district rows are dated. Table counts, total rows, geographic coverage, money, and stable district-score values remain unchanged.

### 2026-08-07 00:37 — Remove exact-representative claims from PIN results
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/lib/action-brief.ts`, `action_brief/engine.py`, `action_brief/models.py`, `web/src/app/api/v1/pin/[pin_code]/route.ts`, `web/src/lib/action-types.ts`, `web/src/components/BriefOverview.tsx`, `tests/test_action_brief.py`, `DATA_CLAIMS.md`, `HANDOFF.md`

Kept plural district-overlap MPs on the root, removed the stale exact-MP/MLA promise, made both action-brief twins return a singular MP only from the medium-confidence PIN→PC estimate, and made singular MLA explicitly unavailable. The PIN API now exposes scope, method, and claim provenance while the deprecated `precise` field is always false; candidate arrays remain intact.

### 2026-08-07 00:52 — Finish the public-account evidence contract
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/lib/area-account.ts`, `web/src/lib/state-account.ts`, `web/src/components/SchemeRow.tsx`, `web/src/components/SchemeDataSection.tsx`, `DATA_CLAIMS.md`

Replaced generic normalized rows with scheme-native district and separately labelled state records, added record-date status and retrieval provenance, split PMGSY money from delivery, rejected stale PM-KISAN `ALL` fragments, restored NRLM detail, and registered current PM-KISAN/JJM/SBM plus PMGSY/FTO metrics. Unknown dates and ambiguous zero placeholders are omitted or named rather than displayed as current facts.

### 2026-08-07 01:06 — Verify NSAP worst-route honesty
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/api/v1/scheme/[scheme]/worst/route.ts`

Verified production `/api/v1/scheme/nsap/worst?state=BIHAR` returns 422 with the registered reason that no district eligibility target exists. It does not query raw `nsap_district`, does not triple districts, and does not rank beneficiary counts as failure; no code change was needed.

### 2026-08-07 01:12 — Restore the Hisaab thesis in the manifesto
**Agent:** Codex
**Status:** ✅ done
**Files:** `MANIFESTO.md`

Rewrote the stale “In practice” examples around the public welfare account: scheme-native evidence first, state context and gaps named, citizen-selected rights/routes second. Removed the false cross-scheme grand-total and red-flag promises, and made all four tenets explicit non-negotiable rules.

### 2026-08-07 01:24 — Ship the one-surface humane ledger UI
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/page.tsx`, `web/src/app/layout.tsx`, `web/src/app/tokens.css`, `web/src/app/base.css`, `web/src/app/forms.css`, `web/src/app/surface.css`, `web/src/app/action.css`, `web/src/app/evidence.css`, `web/src/components/ServiceStart.tsx`, `web/src/components/AccountabilityResult.tsx`, `web/src/components/SchemeDataSection.tsx`, `web/src/components/SchemeRow.tsx`, `web/src/components/ComplaintGuide.tsx`, `design.md`, `.hallmark/log.json`, `.hallmark/preflight.json`

Replaced the issue-first/multi-product shell with one area-first welfare account: direct PIN entry plus state-scoped district fallback, exact ledger records, collapsed secondary state context, named limits, a jumpable citizen-selected action layer, sourced complaint situations/routes, and representatives last. Type/lint/build and SSR HTML passed; browser discovery returned no connected browser, so final visual screenshots remain a production smoke item rather than a fabricated pass.

### 2026-08-07 01:31 — Pass redesign and data-preservation gates
**Agent:** Codex
**Status:** ✅ done
**Files:** `tests/test_public_account_surface.py`, `tests/test_action_brief.py`, `tests/test_loaders.py`

All gates are green: 580 pytest passed / 4 skipped, Ruff clean, TypeScript clean, ESLint clean, Next production build green, and `verify_refresh.py` found no regression across 463 curated files. Local publish plan remains 36 tables / 82,020 rows; 11 complaint families / 52 routes / 7 universal routes; all 744 NFSA rows have reporting dates; 1,888 stable score rows remain byte-equivalent on substantive fields.

### 2026-08-07 10:53 — Stabilize the one-surface account after hydration
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/components/PinEntry.tsx`, `web/src/components/DistrictPicker.tsx`, `web/src/components/ComplaintGuide.tsx`, `web/src/components/SourceLink.tsx`, `web/src/components/AccountabilityResult.tsx`, `web/src/app/forms.css`, `web/src/app/action.css`

Added non-interactive, dimension-stable pre-hydration placeholders; made scheme, representative, route, and situation sources uniquely named; and labelled MPs as district-overlap representatives rather than exact district MPs. Progressive enhancement stays honest because no inert JavaScript control is exposed before hydration.

### 2026-08-07 10:54 — Complete the audited district-fragment migration
**Agent:** Codex
**Status:** ✅ done
**Files:** `scripts/gen_district_aliases.py`, `db/district_aliases.py`, `scripts/build_geodata.py`, `web/public/india-districts.topojson`, `tests/test_district_alias_migration.py`, `DATA_CLAIMS.md`, `data/hisaab.db`

Applied one state-scoped sweep across aliases, topology, civic normalization/re-seed, and score recomputation. The baseline's 944 score labels per FY canonicalize to the same 919 places now served; 25 duplicate fragments per FY merged, every non-merged score stayed substantively identical, and the audit-only metrics snapshot was cleared before publish.

### 2026-08-07 10:55 — Correct NSAP temporal identity and refresh the full dataset
**Agent:** Codex
**Status:** ✅ done
**Files:** `scrapers/scrape_nsap_api.py`, `data/curated/nsap_district_*_latest.json`, `db/schema.py`, `db/connection.py`, `db/loaders.py`, `scripts/verify_refresh.py`, `tests/test_nsap_api.py`, `tests/test_verify_refresh.py`, `DATA_CLAIMS.md`

Re-keyed monthly selection to state + LGD district code + programme, ordered April-to-March, persisted source month/code, and collapsed temporal labels through the canonical district registry. The reviewed refresh serves 2,183 programme rows, 736 district identities, and 31,040,871 beneficiaries under CLAIM-2026-0047; imputed money remains omitted from public claims.

### 2026-08-07 10:56 — Canonicalize state-level evidence identities
**Agent:** Codex
**Status:** ✅ done
**Files:** `db/normalize_states.py`, `web/src/lib/state-account.ts`, `tests/test_pin_constituency_clean.py`, `DATA_CLAIMS.md`, `data/hisaab.db`

Unified NCT DELHI, UTTRAKHAND, TELENGANA, and TAMILNADU with their canonical state names so current state evidence is reachable from the public account. The only row reduction is three duplicate Delhi NSAP-finance state-years; NFSA and UDISE rows and totals are retained, and ambiguous source zeros are labelled rather than hidden as facts.

### 2026-08-07 10:57 — Bind every root claim to exact persisted evidence
**Agent:** Codex
**Status:** ✅ done
**Files:** `scripts/verify_public_claims.py`, `tests/test_public_claim_gate.py`, `.github/workflows/refresh-data.yml`, `DATA_CLAIMS.md`

Added 20 fail-closed contracts covering every static claim ID on the one-surface account. CI now hashes selected geography, period, displayed values, source, retrieval time, and the exact ledger row after alias reload; reviewed final contracts pass and there is deliberately no automatic update path.

### 2026-08-07 10:58 — Remove misleading claims from legacy public APIs
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/api/v1/scheme/[scheme]/route.ts`, `web/src/app/api/v1/scheme/[scheme]/worst/route.ts`, `web/src/app/api/v1/district/[name]/route.ts`, `web/src/app/api/v1/district/[name]/[scheme]/route.ts`, `web/src/app/api/v1/brief/[district]/route.ts`, `web/src/app/api/v1/red-flags/route.ts`, `tests/test_legacy_api_semantics.py`, `DATA_CLAIMS.md`

Made unreported or imputed PM-KISAN, NSAP, PM POSHAN, and NFSA fields NULL; rejected count-only worst rankings; corrected frozen MGNREGA social-audit money from rupees instead of lakhs; and removed unsupported runtime red-flag thresholds. Targeted tests, TypeScript, and ESLint pass.

### 2026-08-07 11:12 — Visually verify the public-account entry surface
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/page.tsx`, `web/src/app/globals.css`, `web/src/app/base.css`, `web/src/app/forms.css`, `web/src/app/surface.css`

Captured full-page Chrome screenshots from the production build at 320, 375, 414, and 768px into `/tmp`, not the repo. The current build's CSS returned 200 and the entry surface showed no horizontal overflow, clipped control, two-line button, or broken hierarchy at those widths.

### 2026-08-07 11:15 — Make temporal claims neutral and sourced
**Agent:** Codex
**Status:** ✅ done
**Files:** `db/snapshot_metrics.py`, `db/snapshots.py`, `queries/trends.py`, `api/routes/schemes.py`, `alerts/digest.py`, `tests/test_snapshot_honesty.py`, `tests/test_alerts.py`, `DATA_CLAIMS.md`

Removed five unsafe snapshot semantics, retained MGNREGA unrecovered money in rupees, bound every neutral point/change to its source and period, and suspended better/worse and new-crossing claims. The first audited local capture has 9,789 sourced rows dated 2026-08-07; focused and full Python gates pass.

### 2026-08-07 11:16 — Preserve snapshot history during Turso publication
**Agent:** Codex
**Status:** ✅ done
**Files:** `scripts/sync_turso.py`, `tests/test_sync_turso.py`, `DATA_CLAIMS.md`

Made `metrics_snapshot` append-only across production syncs, omitted local surrogate IDs so remote history cannot collide, and verify each local dated payload exactly while allowing older remote dates to remain. Four targeted sync contract tests pass.

### 2026-08-07 11:18 — Visually verify the one-surface account result
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/page.tsx`, `web/src/app/surface.css`, `web/src/components/SchemeRow.tsx`, `web/src/components/ComplaintGuide.tsx`

Captured full-page PIN-result screenshots at 320px and 768px on the uncontested current build. Both widths have exact viewport scroll width, every stylesheet returned 200, the public account and 17 claim bindings rendered, and the single action button remained unclipped; artifacts stay in `/tmp`.

### 2026-08-07 11:22 — Correct and republish the production snapshot
**Agent:** Codex
**Status:** ✅ done
**Files:** `data/hisaab.db`, `scripts/sync_turso.py`, `DATA_CLAIMS.md`

Verified the 13,957-row 2026-08-06 production payload against its 3.9 MB backup (SHA-256 `11addda24054e877bca61aa3f9d40e3b2c7d29a975c34994be0773d9afe5a9c1`), removed that unaudited derived date, and appended the real 9,789-row audited capture dated 2026-08-07. Turso verified all 36 tables / 91,743 local payload rows; every snapshot row has a source and none uses an excluded metric contract.

### 2026-08-07 11:28 — Aggregate NSAP programmes in the legacy district API
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/api/v1/district/[name]/[scheme]/route.ts`, `tests/test_legacy_api_semantics.py`, `DATA_CLAIMS.md`

Production smoke exposed that the generic district adapter returned one arbitrary NSAP programme row. The endpoint now sums all named programme counts for the district-year, lists the included programmes, keeps imputed money NULL, and explicitly refuses an eligibility-rate inference; full Python and frontend gates pass.

### 2026-08-07 12:02 — Audit Hisaab through universal citizen stress cases
**Agent:** Codex
**Status:** ✅ done
**Files:** `design.md`, `.hallmark/log.json`

Used wage-worker, salaried-citizen, low-literacy, teenager, activist, helper, and screen-reader contexts as tests of one shared flow rather than persona modes. The resulting product rule is simple first, exact underneath, action when requested; AI remains optional navigation/comprehension infrastructure.

### 2026-08-07 12:03 — Make the public account losslessly scannable
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/components/AccountabilityResult.tsx`, `web/src/components/SchemeDataSection.tsx`, `web/src/components/SchemeRow.tsx`, `web/src/components/ComplaintGuide.tsx`, `web/src/app/action.css`, `web/src/app/base.css`, `web/src/app/evidence.css`, `web/src/app/surface.css`, `DATA_CLAIMS.md`

Converted the full ledger, coverage limits, entitlement, situations, case outline, and routes to native progressive disclosure while retaining every exact record and all 52 verified routes in SSR and print. Shortened the universal action copy, kept the CAPTCHA boundary visible, removed mobile text-size suppression, and registered the presentation contract as DERIVED-2026-0014.

### 2026-08-07 12:04 — Gate the universal two-layer account
**Agent:** Codex
**Status:** ✅ done
**Files:** `tests/test_public_account_surface.py`, `.hallmark/log.json`

Added regression coverage for closed-by-default lossless disclosures and complete evidence/route maps. All 621 Python tests pass (4 skipped), the 20-dataset public-claim gate passes, and frontend lint, TypeScript, and production build pass; SSR smoke retains the full record and complaint payload. Interactive visual QA is pending because no browser backend was connected.

### 2026-08-07 12:08 — Verify production data before UI publish
**Agent:** Codex
**Status:** ✅ done
**Files:** `scripts/sync_turso.py`, `web/.env.local`

Ran the canonical Turso sync after the feature commit. All 36 tables and 91,743 local payload rows verified; the 9,789-row metrics snapshot remained append-only and all 42 indexes/views were published.

### 2026-08-07 12:14 — Publish and smoke the universal account
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/components/SchemeRow.tsx`, `web/src/components/ComplaintGuide.tsx`, `DATA_CLAIMS.md`

Pushed the scannable account to production after a 36-table/91,743-row verified Turso sync. CI run 31154583955 passed; entry, Gayaji account, MGNREGA help, UDISE+ education help, general help, PIN identity, NSAP aggregation, and the fail-closed NSAP worst endpoint all returned the expected production contract.

### 2026-08-07 13:02 — Rebuild Hisaab as a guided civic ledger
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/components/ServiceStart.tsx`, `web/src/components/PinEntry.tsx`, `web/src/components/DistrictPicker.tsx`, `web/src/components/AccountabilityResult.tsx`, `web/src/components/SchemeDataSection.tsx`, `web/src/components/SchemeRow.tsx`, `web/src/components/ComplaintGuide.tsx`, `web/src/app/tokens.css`, `web/src/app/base.css`, `web/src/app/forms.css`, `web/src/app/surface.css`, `web/src/app/evidence.css`, `web/src/app/action.css`, `design.md`, `DATA_CLAIMS.md`

Replaced the visually flat audit sheet with an editorial entry, bounded area masthead, dimension-labelled service index, structured evidence panels, and numbered action steps. The redesign changes hierarchy and component voice only: all evidence, sources, route rungs, CAPTCHA handoff, and personal-data boundaries remain intact.

### 2026-08-07 13:03 — Gate the guided-ledger implementation
**Agent:** Codex
**Status:** ✅ done
**Files:** `tests/test_public_account_surface.py`, `web/src/app/globals.css`, `.hallmark/log.json`

Added task-orientation and dimension-label regression checks; all 622 Python tests pass (4 skipped), the 20-dataset public-claim gate passes, frontend lint/TypeScript/build pass, and every tested text/background pair exceeds WCAG 4.5:1. Final screenshot/zoom inspection remains pending because no interactive browser backend is connected, and the Hallmark stamp records that limitation rather than claiming a visual pass.

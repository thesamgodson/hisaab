# Learnings — Hisaab

Failure postmortems + corrective rules only.

### 2026-08-04 (night) — A fresher-but-worse dataset silently replaced a better one
**Failure:** A subagent restoring DAY-NRLM found a live LokOS CDN endpoint
(`cdn.lokos.in/lokos-in/fdm/prod/IN/FDM_OVERALL.json`) that is **state-level
only**, wrote it over the district-level curated file, and loaded it — turning
715 district rows into 34 `district='ALL'` rows in both the curated JSON and the
DB. Caught by diffing the working file against `git show HEAD:` before handoff;
fully reverted. `atomic_write_json` did NOT catch it: that guard only blocks
**empty** overwrites, not lower-granularity ones.
**Rules:**
1. A refresh must never reduce granularity. Loaders/scrapers replacing a
   district-level table need a guard: if the incoming batch has fewer distinct
   `(state, district)` pairs than the existing table (or is all `district='ALL'`),
   refuse and report instead of writing.
2. Any subagent that touches curated data must have its output diffed against
   `git show HEAD:<path>` (row count, granularity, date) before its work is
   accepted — "tests pass and ruff is clean" does not detect data regression.
3. Currency is not automatically better than granularity. When a new source
   offers only coarser data, it becomes an *additional* artifact, never a
   replacement.

### 2026-08-04 — Loader param-stamping nearly relabeled March data as FY2025-26
**Failure:** District loaders stamped every record with the CLI --fin-year instead of the record's own year; a refresh load would have labeled 5-month-old rows as current-year data — a provenance lie the UI would have served confidently.
**Rule:** The record's own fin_year always wins; CLI/param years are fallback-only. Any field that carries provenance (fin_year, scraped_at, source_url) must flow from the scrape record, never from load-time context.

### 2026-08-04 — "Monotonic" guards must fail loudly
**Failure:** The alias-registry generator's import of the existing registry failed silently from script-dir sys.path and returned {} — the "monotonic" registry shrank 167→91 twice before the cause was found.
**Rule:** A guard whose failure mode equals the disaster it guards against (silent empty fallback) is worse than no guard. Import failures in guards are hard errors; only genuine absence (file doesn't exist) may soften.

### 2026-08-04 (evening) — Delete-then-scrape loses data when the scrape dies
**Failure:** Clearing curated finance files before re-scraping (to defeat run_all's skip-if-exists) left the working tree without them twice when data.gov.in collapsed mid-scrape — only git restore saved the load path.
**Rule:** Scrapers write to a temp name and atomically rename over the old file ONLY on non-empty success. Never pre-delete the previous good artifact to force a refresh; add a --force flag to the orchestrator instead.

### 2026-08-04 (evening) — MGNREGA moved to *.dord.gov.in and gated MIS behind a captcha
**Fact:** nrega.nic.in now redirects to nrega.dord.gov.in; report mirrors moved to mnregaweb2/4.dord.gov.in; the MIS report index (URL signer) is captcha-gated. Signed-URL validation ("URL Tampered") blocks direct report fetches.
**Rule:** We do not automate captcha bypass — ever. The refresh path is the un-gated citizen flow (mnregaweb2.dord.gov.in/netnrega/homestciti.aspx state→district pages), which needs a rebuilt scraper. NRLM similarly migrated to LokOS (lokos.in) and needs a new integration.

### 2026-08-04 — Government portals fail in four different ways in one day
**Fact:** nreganarep.nic.in = TCP-dead while nrega.nic.in is fine; nrlm.gov.in = whole domain 404; data.gov.in = platform-wide read timeouts; MyNeta = fine but new election pages 404 on bare index.php while ?action=show_winners works.
**Rule:** Per-scheme freshness must be the public truth (it is, via /freshness), refresh jobs must tolerate per-portal failure without losing prior data (truncate-only-when-file-exists guard), and portal outages are recorded, never papered over.

### 2026-08-04 — The repo you cloned is not the repo that deployed
**Failure:** Prod ran code from a GitHub-merged PR the local clone never pulled; every local grep for the failing table came up empty and the first analysis wrongly concluded "missing tables in Turso". Only `vercel logs` on the live deployment revealed `district_lineage`.
**Rule:** When prod behavior contradicts the code you're reading, fetch origin AND read the deployment's runtime logs before theorizing. `git log origin/main..main` lies until you `git fetch`.

### 2026-08-04 — revalidate on a request-less route handler = build-time execution
**Failure:** Adding `export const revalidate = 3600` to freshness/stats made Next prerender them during `next build`; CI (no DB creds) broke while local builds (with .env.local) passed.
**Rule:** Route handlers that touch external services and don't read `request` need `export const dynamic = "force-dynamic"` unless build-time execution is explicitly intended — and CI must build WITHOUT production credentials to catch this class.

### 2026-08-04 — Porting business logic forks the truth
**Failure:** The March frontend migration hand-ported `queries/composite.py` to `web/src/lib/scores.ts`, and separately inlined a 60/40 variant into the MP/constituency routes. The public site now publishes two different "accountability scores" for the same district, and neither can be reconciled against the CLI.
**Rule:** Derived numbers (scores, grades, red flags) are computed in exactly one place — at publish time, into DB tables — and every surface (web, CLI, briefs) reads them. Never port an algorithm; move its output.

### 2026-08-04 — A green CI badge can assert nothing
**Failure:** CI never builds the SQLite fixture, so the three integration test files (`test_api.py`, `test_new_api.py`, `test_data_integrity.py`) skip at module level. 500 tests "pass" while the deployed product's hero flow 500s.
**Rule:** CI must run `run_all.py --load-only` (or restore a fixture DB) before pytest, and a prod smoke probe must hit the PIN flow after every deploy.

### 2026-08-04 — Manual DB pushes rot silently
**Failure:** Turso (prod) was populated by hand in March; local `data/hisaab.db` kept evolving (new PIN tables, state fixes). Nobody noticed prod's hero flow 500ing because nothing verified prod schema against local schema.
**Rule:** Any table added to `db/schema.py` must ship with (a) a scripted local→Turso sync path and (b) a prod smoke probe (curl the endpoint that reads it) before the feature is called done.

### 2026-08-04 (night) — Concurrent agent writes + main-session load published unverified data
**Failure:** While the main session ran `run_all.py --load-only` + Turso sync for the NRLM refresh, a background subagent had (correctly, per its brief) refreshed 40 NSAP/finance curated files. The load glob swept those files in, and the sync published them to prod BEFORE the main session's diff-vs-HEAD acceptance pass ran. Verification happened minutes later and everything was clean — but only by luck; a regressed file would have been served.
**Rule:** When any agent that writes curated data is running, `--load-only`/sync are gated: either wait for the agent's completion + acceptance diff, or load with an explicit table allowlist. The acceptance diff comes BEFORE the first load that can sweep the files, not after.

### 2026-08-04 (close-out) — A shared load-fallback fin_year silently relabeled frozen data
**Failure:** Changing `run_all.py --fin-year` default from 2024-2025 to 2025-2026 (correct, so the weekly cron scrapes the right year for MGNREGA/PMAY-G) silently relabeled the FROZEN FY2024-25 `misappropriation` + `issues_reported` tables as FY2025-26 — because those curated files carry no fin_year field and the loader uses `r.get("fin_year") or fin_year`. A provenance lie (CLAIM-2026-0001 pins them to FY2024-25) that also broke 4 api tests. The old default happened to match the frozen year by luck; the coupling was invisible until the default moved.
**Rule:** Every curated record that will be loaded must carry its OWN fin_year (and scraped_at, source_url) — landmine #3 applies to STATIC/frozen data too, not just live scrapes. A load-time fallback default is a latent relabeling bomb: it must only ever apply to records that legitimately have no year, and no served table should depend on it. When a table is frozen, stamp its provenance INTO the curated file so no orchestrator default can move it.

### 2026-08-04 (close-out) — A from-scratch DB build wipes tables that --load-only doesn't own
**Failure:** `rm hisaab.db` to apply a schema change silently emptied the civic tables (pin_district_mapping, constituency_district, ac_district, mp_info, mla_info, district_lineage, pin_constituency) — they are seeded by `constituency.ingest` (+ a manual pin_constituency load), NOT by `run_all.py --load-only`. `sync_turso` mirrors EVERY table with DROP+CREATE+INSERT, so publishing that DB would have recreated those tables EMPTY on prod and 500'd the PIN flow — the exact March-2026 disaster. The scheduled refresh workflow has the same shape (only `--mla-only`/`--mp-only`), so its first real run would have wiped prod too.
**Rule:** (1) Never `rm hisaab.db` without re-seeding the civic tables (`python -m constituency.ingest`) before any sync — or use ALTER/migration instead of a rebuild for schema changes. (2) `sync_turso` now guards this at the publish boundary: it refuses to replace a populated remote table with an empty local one (KEPT, not wiped). Any publish path that can push a from-scratch DB needs that guard — a wipe protection at the boundary beats remembering to re-seed.

### 2026-08-05 — Background subagents leak: idle teammates run for the whole session
**Failure:** Sam flagged agents "running 9-13 hours." Investigation: four teammates from the PREVIOUS session (nrlm-discovery, datagovin-retry, pmkisan-nfsa-hunt, pmayg-hunter) were still alive — they'd completed their discovery work hours earlier, gone idle/available, and NEVER terminated. Agents spawned via the Agent tool run as `in_process_teammate`s that persist for the session's lifetime waiting for more messages; they do not self-reap on completion, and prompt-level timeouts ("--max-time 30, 12-min budget") are advisory, not enforced — a hung one runs indefinitely. The long-lived session container spanned both work sessions (same session id), so every teammate ever spawned accumulated runtime.
**Rule:** TaskStop every background agent the moment its result is in hand — completion does NOT kill it. Prefer synchronous agents (run_in_background:false) that return-and-die for bounded tasks. At session start AND end, sweep for leftover teammates: `TaskStop` a dummy id and read the "Running teammates:" list in the error, then stop each. Never rely on an agent honoring a prompt-level time budget.

### 2026-08-05 — "Transient" sync failure was deterministic: a guard changed the invariants downstream code assumed
**Failure:** Landmine #12 recorded the libsql `KeyError('result')` on index push as transient ("retries clear it"). Two CI publishes then failed at the SAME statement through 3 and then 7 retries. Truth: the wipe-guard (added 8d48501) KEEPS tables it refuses to overwrite — so their old indexes survive, and the replayed `CREATE INDEX` (sqlite_master strips `IF NOT EXISTS` from stored DDL) collides deterministically. It only ever "cleared with retries" locally because local civic tables are populated → DROP+recreate → no surviving index. libsql compounds it by returning an error body without a `result` key, so the client raises KeyError and the "already exists" text the retry helper looks for never surfaces.
**Rules:** (1) When adding a guard that changes state-shape invariants (kept-instead-of-replaced), audit every later phase that assumed the old shape — the sync's index phase assumed "tables were just recreated bare". (2) A retry loop that fails N/N times on the SAME input is evidence of determinism, not bad luck — log WHICH input (the fix that cracked this was labeling retries with the SQL instead of "index"). (3) Idempotent DDL replay = drop-then-create in one batch (views already did this; indexes now match). (4) A third-party client can mask the real error class — verify what the server actually said before trusting the exception type.

### 2026-08-05 — A state-blind alias table quietly rewrote another state's districts
**Failure:** `constituency/fuzzy_match.py` kept a bare-name alias dict ("AURANGABAD"→"CHHATRAPATI SAMBHAJINAGAR", meant for Maharashtra) and civic ingest pushed every state's districts through it — 26 BIHAR pins were served under Maharashtra's renamed district, Delhi's NEW DELHI district vanished into "DELHI", and the damage was invisible because the load-time canonical pass (state-aware) simply left the wrong labels alone: a normalizer can't restore information a previous normalizer destroyed. Found only because a NEW test for the mp_info migration collided with `UNIQUE(constituency, district)` — pulling the thread exposed the whole family.
**Rules:** (1) India reuses names across states at every level — PC names, district names, even (PC, district) pairs (HAMIRPUR/HAMIRPUR). Any uniqueness constraint, join, or alias key on a civic name that omits `state` is a landmine, no exceptions. (2) When two normalizers exist for one identity, exactly one may write stored labels; the other (fuzzy matchers, report tooling) must be read-only. (3) A guard that runs AFTER corruption (normalize-at-load) does not protect against corruption at ingest — validate at the boundary where the label is first written. (4) When a test you wrote for defect A fails for unrelated reason B, B is usually a sibling of A — investigate before "fixing the test".

### 2026-08-05 — Publish-before-commit orphans prod data when publish fails late
**Failure:** Round-1 babysit: all 30 tables pushed to Turso, THEN the index phase died → smoke and the curated-data commit were skipped. Prod served freshly-scraped values that no git commit described — invisible drift between the source of truth (curated-in-git) and what users read.
**Rule:** In any pipeline where git is the canon and a remote store is derived, land the canon FIRST (verify → load → commit → publish → smoke). A publish failure must leave "git ahead of prod" (self-healing on the next sync), never "prod ahead of git". Applied to refresh-data.yml (ca51fd6).

### 2026-08-06 — Specialized reviewer agents truncate to silence on multi-file audits
**Failure:** Both `accessibility-auditor` and `code-reviewer` dispatches (each given a ~6-file hero-surface audit) went idle "available" WITHOUT delivering any report, twice each (initial run + one resend ping). Zero findings recovered from either; both stopped as poisoned per the 2-corrections rule. This is the failure mode the local agent roster itself documents: the specialized `*-reviewer` agent types carry a low maxTurns cap and "truncate to an empty result on deep tasks" (the deep-redteam skill exists precisely because of this).
**Rules:** (1) Scope specialized reviewer agents to ONE file or one tight diff; anything wider goes to a general-purpose agent (no low cap) with an explicit checklist, or gets reviewed inline by the orchestrator. (2) An idle notification is not a report — treat "idle without deliverable" as failure immediately; ping at most once. (3) When two sibling agents fail identically, stop diagnosing the agents and suspect the agent TYPE's constraints.

### 2026-08-06 — Session artifacts buried the repo root until Sam couldn't find his own docs
**Failure:** Playwright screenshots and DOM dumps from three different sessions (March + August) accumulated at the repo root — 12 stray PNGs, a `.playwright-mcp/` debris directory, stale mypy/pytest/ruff caches. All gitignored, so every `git status` looked clean while the actual directory became unnavigable; Sam couldn't find ONBOARDING.md sitting right there. "Invisible to git" had been quietly treated as "doesn't count as mess".
**Rules:** (1) Session artifacts (screenshots, probe dumps, scratch logs) are written to the session scratchpad directory, NEVER the repo — when a tool defaults to a relative path (Playwright MCP screenshots), pass the absolute scratchpad path explicitly. (2) gitignored ≠ clean: the human navigates the filesystem, not the git index — leave the working tree as navigable as the commit history. (3) Before ending a session, sweep the repo root for artifacts the session created and delete them.

### 2026-08-06 09:55 — `npm run build` kills a running `next dev` on the same tree
**Agent:** Claude Code
**Status:** ✅ done
**Files:** `web/.next/`

`next build` and `next dev` share `web/.next/`. Running the build gate while a dev server is up replaces the dev webpack runtime with the production one; every subsequent dev request 500s with `Cannot find module './873.js'` and the dev compiler cannot recover it — touching sources does not help. Rule: before running the `npm run build` gate on this repo, expect to restart any dev server afterwards (`npm run dev`), or run the build in a separate checkout.

### 2026-08-06 15:57 — A bare SQLite path silently created a fake root database
**Agent:** Codex
**Status:** ✅ done
**Files:** `hisaab.db` (removed), `data/hisaab.db`

**Failure:** A one-off audit opened `sqlite3.connect('hisaab.db')` from the repository root instead of `data/hisaab.db`; SQLite silently created a zero-byte database, making the missing-table error look like a damaged project database. The accidental empty file was removed immediately and the actual database was never touched.
**Rules:** (1) This repository’s database path is `data/hisaab.db`, never the root. (2) Inspection scripts must open SQLite read-only with a URI (`file:data/hisaab.db?mode=ro`) so a typo fails instead of creating a new file. (3) Before any database command, resolve and print the exact path; the “never remove the database without civic re-seed” rule applies to the real data asset, so path ambiguity is unacceptable.

### 2026-08-06 16:04 — Clear generated Next types after deleting App Router pages
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/.next/types/validator.ts`, `web/src/app/action/[pin]/page.tsx`, `web/src/app/district/[name]/page.tsx`

A standalone `tsc --noEmit` can read stale `.next/types` route declarations after page deletion and report false missing-module errors. Remove the generated `web/.next` build cache safely before rerunning typecheck; never treat generated route declarations as source failures.

### 2026-08-06 16:24 — Never derive or label a cross-scheme percentage generically
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/components/SchemeRow.tsx`, `db/schema.py`, `tests/test_cross_scheme.py`

**Failure:** The evidence row divided any `units_completed` by any `units_target` and called any legacy `utilization_pct` a generic percentage, turning a PM POSHAN daily snapshot into false delivery and fund claims. **Rule:** cross-scheme UI may format a percentage only when the view publishes a semantically named, source-valid percentage; placeholder zeros and incomparable targets become NULL at the view boundary, with regression tests for each exceptional scheme.

### 2026-08-06 16:31 — Do not use a browsing archetype or Latin font as a civic default
**Agent:** Codex
**Status:** ✅ done
**Files:** `design.md`, `SERVICE_DESIGN.md`

**Failure:** The prior design named an Index-First browsing macrostructure and Aptos-first stack before testing whether either fit a stressed, multilingual grievance task. **Rule:** choose the service job before the visual genre: Hisaab uses a staged casework shell, tests issue language with citizens, and treats Aptos as an optional Latin face while Noto/system script fonts carry complete human-reviewed language variants.

### 2026-08-06 17:58 — A UI hotfix is incomplete while a twin still emits the false claim
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/lib/action-brief.ts`, `action_brief/diagnosis.py`, `directory/seed_data.py`

**Failure:** The web layer stopped interpreting PM POSHAN, NFSA, and NSAP placeholder/snapshot metrics as shortfalls, but the Python action brief continued emitting those claims and a stale seeder could restore deliberately removed phone numbers. **Rule:** after every claim correction, search every API, card, seeder, fixture, and language twin for the old semantic pattern; source truth includes all paths that can publish or repopulate it.

### 2026-08-06 18:20 — Do not copy a broken twin to manufacture parity
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/lib/action-brief.ts`, `action_brief/diagnosis.py`, `web/AGENTS.md`, `DATA_CLAIMS.md`

**Failure:** The first parity fix copied runtime thresholds between twins before checking their underlying units and denominators; the audit then found rupees labelled as lakhs, 0/0 recovery and utilization flags, and FY-versus-cumulative mismatches. **Rule:** parity is not correctness. For derived civic judgments, verify source semantics first, require a registered load-time methodology, and suspend the claim in every twin rather than aligning two unsupported formulas.

### 2026-08-06 18:20 — SQLite inspection must be read-only, every time
**Agent:** Codex
**Status:** ✅ done
**Files:** `hisaab.db` (removed), `data/hisaab.db`

**Failure:** Despite the existing logbook law, a schema probe again invoked `sqlite3 hisaab.db` at repo root and silently created a zero-byte fake database. It was verified empty and removed; the 13,697,024-byte `data/hisaab.db` was untouched. **Rule:** all future probes must use `sqlite3 'file:data/hisaab.db?mode=ro'` or an equivalent read-only URI; never type a bare database filename.

### 2026-08-06 18:33 — Verified prose is not structured route metadata
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/components/ComplaintGuide.tsx`, `data/curated/grievance_channels_all_latest.json`

**Failure:** The first implementation inferred phone/offline/app/online action types from words inside source-verified route descriptions, then changed button verbs from that inference. **Rule:** provenance makes prose citable, not machine-structured. Controls may use explicit fields such as the verified destination and phone; prerequisites, channel type, filing action, proof, or waiting period remain absent until curated as fields with sources.

### 2026-08-06 18:35 — Visual emphasis is a claim about relevance
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/components/ComplaintGuide.tsx`, `data/curated/grievance_channels_all_latest.json`

**Failure:** Even after the copy denied a guaranteed ladder, a filled primary panel still visually recommended `channels[0]` for every selected trigger, although the registry contains no trigger-to-route mapping. **Rule:** hierarchy, button weight, default expansion, and ordering are claim surfaces. Without sourced applicability metadata, render routes equally and state exactly what the ordering does and does not mean.

### 2026-08-06 19:51 — A valuable secondary layer must not colonize the product
**Agent:** Codex
**Status:** ✅ done
**Files:** `MANIFESTO.md`, `design.md`, `web/src/app/page.tsx`

**Failure:** The redesign correctly improved complaint routes but made grievance casework the entire entry architecture, displacing Hisaab's founding job: a sourced, area-level public account of welfare money and delivery for citizens, helpers, and journalists. **Rule:** derive product hierarchy from the manifesto's primary question before optimizing a new feature. Evidence leads; accountability explains who must answer; complaint tools help a person act on what they found.

### 2026-08-06 20:37 — A useful action layer must not replace the account
**Agent:** Codex
**Status:** ✅ done
**Files:** `MANIFESTO.md`, `design.md`

Corrective rule: begin with Hisaab's irreducible question—where public welfare money and delivery went in an area—then attach complaint guidance and representatives as optional action. Never let the strongest newly-built secondary feature redefine the product thesis.

### 2026-08-07 00:18 — Use the project interpreter for every data command
**Agent:** Codex
**Status:** ✅ done
**Files:** `learnings.md`

**Failure:** The first `run_all.py --load-only` attempt used macOS `/usr/bin/python3` (3.9), which cannot import `datetime.UTC`; it exited before opening or changing the database. **Rule:** run repository Python commands with `.venv/bin/python` and confirm the interpreter before any refresh, migration, test, or publish gate.

### 2026-08-07 11:03 — A script entry point must prove its import path
**Agent:** Codex
**Status:** ✅ done
**Files:** `scrapers/scrape_nsap_api.py:20-36`, `tests/test_nsap_api.py`

**Failure:** Directly invoking the NSAP scraper initially failed after the network pull because imports assumed package execution and the repository root was absent from `sys.path`. **Rule:** every supported data command must be tested in the exact documented invocation form; establish the root before importing project modules so a completed pull cannot fail at persistence.

### 2026-08-07 11:04 — Never reseed civic PIN data from an incomplete cache
**Agent:** Codex
**Status:** ✅ done
**Files:** `constituency/ingest.py`, `data/raw/pin_directory/`, `data/hisaab.db`

**Failure:** A full civic ingest hit a network timeout, then revealed cached PIN pages 0, 1, and 46 were missing; continuing would have replaced a complete 19,232-row table with partial coverage. **Rule:** when the API and cache cannot prove completeness, stop before writes and re-seed from a verified database snapshot; run PC/AC/MP/MLA bounded modes separately rather than trusting a partial full ingest.

### 2026-08-07 11:13 — A screenshot is invalid until its asset build is identified
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/.next/BUILD_ID`, `web/.next/static/css/`

**Failure:** The first local screenshots hit an older Next server already bound to `127.0.0.1:3100`; its HTML referenced a CSS hash absent from the current `.next`, so a healthy design appeared completely unstyled. **Rule:** before visual QA, use an uncontested port, compare the served build/CSS hash to the current `.next`, and require every linked stylesheet to return 200; never diagnose UI from a stale server capture.

### 2026-08-07 11:16 — A wipe guard can conceal remote rows from the publish total
**Agent:** Codex
**Status:** ✅ done
**Files:** `scripts/sync_turso.py`, `data/hisaab.db`

**Failure:** The first publish kept a populated remote `metrics_snapshot` because the local table was empty, then reported only the local payload total; inspection found 13,957 remote derived rows with five misleading metric semantics. The same mirror strategy would have deleted history once CI produced a non-empty one-date table. **Rule:** inspect and report retained remote counts, classify temporal tables as append-only, exclude surrogate IDs during append, verify exact dated payloads, and audit every kept table's public semantics before declaring a sync complete.

### 2026-08-07 11:28 — A generic single-row adapter must prove source grain
**Agent:** Codex
**Status:** ✅ done
**Files:** `web/src/app/api/v1/district/[name]/[scheme]/route.ts`, `tests/test_legacy_api_semantics.py`

**Failure:** Post-deploy smoke showed the legacy district endpoint selecting one unordered NSAP programme row and labelling its beneficiary count as district NSAP, even though three programme rows exist. **Rule:** before reusing a generic `queryOne` adapter, assert the table's unique grain; multi-row schemes must aggregate with visible component labels or return the complete row set, never an arbitrary row.

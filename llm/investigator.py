"""Investigative assistant engine for Hisaab.

Flow:
  1. Receive a natural language question + user API key + provider choice.
  2. Inject the DB schema and ask the LLM to write a single SELECT statement.
  3. Validate the SQL (SELECT only — no mutations allowed).
  4. Execute the query against the local SQLite database.
  5. Ask the LLM to produce a narrative answer with citations sourced from the results.
  6. Return a structured InvestigationResult.

Security properties:
  - API keys are never stored, logged, or included in any response.
  - Only SELECT statements are executed; all mutation keywords are rejected.
  - Result row count is capped at MAX_RESULT_ROWS to prevent excessive data exposure.
"""

from __future__ import annotations

import re
import sqlite3
import textwrap
from dataclasses import dataclass, field
from typing import Any

from db.connection import get_connection
from db.schema import SCHEMA
from llm.providers import Provider, generate

# Maximum rows returned to the LLM for narrative generation.
# Large result sets are truncated — the SQL is still executed in full and
# the truncation is noted in the narrative prompt.
MAX_RESULT_ROWS = 50

# SQL keywords that indicate a mutating statement — reject immediately.
_MUTATION_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)

# Source URLs known per table — used to build the `sources` list.
# Populated from the most recent scraped rows at query time.
_TABLE_SOURCES: dict[str, str] = {
    "misappropriation": "https://nrega.nic.in",
    "fto_status": "https://nrega.nic.in",
    "fto_pendency": "https://nrega.nic.in",
    "issues_reported": "https://nrega.nic.in",
    "financial_statement": "https://nrega.nic.in",
    "pmgsy_progress": "https://pmgsy.dord.gov.in",
    "pmgsy_district": "https://pmgsy.dord.gov.in",
    "pmayg_district": "https://report.pmayg.dord.gov.in",
    "pmayg_finance": "https://report.pmayg.dord.gov.in",
    "pmkisan_district": "https://data.gov.in",
    "jjm_district": "https://ejalshakti.gov.in",
    "jjm_allocation": "https://ejalshakti.gov.in",
    "pmposhan_district": "https://pmposhan-ams.education.gov.in",
    "pmposhan_finance": "https://data.gov.in",
    "nsap_district": "https://data.gov.in",
    "nsap_finance": "https://data.gov.in",
    "nfsa_district": "https://nfsa.gov.in",
    "nfsa_allocation": "https://nfsa.gov.in",
    "sbm_district": "https://sbm.gov.in",
    "nrlm_district": "https://nrlm.gov.in",
    "udise_state": "https://api.udiseplus.gov.in",
}

_SCHEMA_SUMMARY = textwrap.dedent("""
    SQLite database with these tables and views (all amounts in lakhs of rupees unless noted):

    TABLES:
    - misappropriation(district, state, fin_year, cases_reported, amount_reported, amount_to_recover, amount_recovered, amount_unrecovered, recovery_rate_pct, source_url)
    - fto_status(district, state, fin_year, total_fto_generated, fto_processed_by_bank, transactions_processed, source_url)
    - fto_pendency(bank_name, state, fin_year, pending_1_7_days, pending_8_15_days, pending_16_30_days, pending_over_30_days, total_pending, source_url)
    - issues_reported(district, state, fin_year, misappropriation_issues, misappropriation_amount, total_issues, total_amount, source_url)
    - financial_statement(district, state, fin_year, total_availability, cumulative_expenditure, utilization_pct, source_url)
    - pmgsy_district(district, state, fin_year, roads_sanctioned, roads_completed, length_sanctioned_km, length_completed_km, value_of_projects_cr, expenditure_cr, source_url)
    - pmayg_district(district, state, fin_year, houses_sanctioned, houses_completed, houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct, source_url)
    - pmayg_finance(state, fin_year, allocated_lakhs, released_lakhs, utilized_lakhs, source_url)
    - pmkisan_district(district, state, fin_year, beneficiaries_registered, beneficiaries_paid, amount_paid_lakhs, installment, source_url)
    - jjm_district(district, state, fin_year, total_households, households_with_tap, coverage_pct, funds_released_lakhs, funds_utilized_lakhs, source_url)
    - jjm_allocation(state, fin_year, allocated_crores, released_crores, expended_crores, source_url)
    - pmposhan_district(district, state, fin_year, schools_covered, children_enrolled, children_fed, funds_released_lakhs, funds_utilized_lakhs, utilization_pct, source_url)
    - pmposhan_finance(state, fin_year, allocated_lakhs, released_lakhs, utilized_lakhs, source_url)
    - nsap_district(district, state, fin_year, scheme_type, beneficiaries_eligible, beneficiaries_paid, amount_paid_lakhs, source_url)
    - nsap_finance(state, fin_year, released_lakhs, beneficiaries, source_url)
    - nfsa_district(district, state, fin_year, ration_cards_total, ration_cards_active, allocation_mt, offtake_mt, offtake_pct, source_url)  [allocation_mt/offtake_mt in METRIC TONNES, not lakhs]
    - nfsa_allocation(state, fin_year, grain_type, allocation_mt, offtake_mt, source_url)  [metric tonnes]
    - sbm_district(district, state, fin_year, total_villages, odf_plus_villages, odf_plus_pct, one_star_villages, three_star_villages, five_star_villages, source_url)
    - nrlm_district(district, state, fin_year, shgs_total, shgs_new, members_total, rf_shgs_provided, rf_amount_lakhs, source_url)
    - udise_state(state, fin_year, total_schools, total_students, total_teachers, ptr_primary, ptr_secondary, ger_primary, dropout_primary, source_url)
    - scrape_runs(state, fin_year, report_name, record_count, source_url, scraped_at)

    VIEWS (pre-joined for convenience):
    - scheme_finance(scheme, state, district, fin_year, allocated_lakhs, released_lakhs, expended_lakhs, utilization_pct, source_url)
    - scheme_delivery(scheme, state, district, fin_year, units_target, units_completed, units_label, delivery_pct, source_url)
    - money_flow(scheme, state, district, fin_year, allocated_lakhs, released_lakhs, expended_lakhs, utilization_pct, units_target, units_completed, units_label, source_url)

    CONVENTIONS:
    - State names are UPPER CASE (e.g. 'BIHAR', 'TAMIL NADU')
    - District names are UPPER CASE (e.g. 'VILLUPURAM')
    - fin_year format: '2024-2025'
    - PMGSY financials are in crores (multiply by 100 for lakhs); all other financial tables are in lakhs
    - NFSA/nfsa_allocation tracks metric tonnes, not rupees — do not mix with lakhs columns
    - district='ALL' means state-level aggregate row
""").strip()


@dataclass
class InvestigationResult:
    """Structured response from the investigative assistant."""

    question: str
    sql: str
    results: list[dict[str, Any]]
    narrative: str
    sources: list[dict[str, str]]
    provider_used: str
    model_used: str
    truncated: bool = False


def _extract_sql(raw: str) -> str:
    """Pull the first SQL SELECT statement from an LLM response.

    The model may wrap it in a markdown code block or add prose. We extract
    the bare SQL to execute.
    """
    # Try to find a fenced code block first.
    fence_match = re.search(r"```(?:sql)?\s*\n?(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # Fall back: take everything from the first SELECT to the final semicolon or end.
    select_match = re.search(r"(SELECT\b.*)", raw, re.DOTALL | re.IGNORECASE)
    if select_match:
        candidate = select_match.group(1).strip()
        # Trim trailing prose after the semicolon if present.
        semi_match = re.search(r"(.*?;)", candidate, re.DOTALL)
        if semi_match:
            return semi_match.group(1).strip()
        return candidate

    return raw.strip()


def _validate_sql(sql: str) -> None:
    """Raise ValueError if the SQL contains any mutation or dangerous keyword."""
    mutation_match = _MUTATION_PATTERN.search(sql)
    if mutation_match:
        raise ValueError(
            f"SQL contains disallowed keyword '{mutation_match.group()}'. "
            "Only SELECT statements are permitted."
        )
    normalised = sql.strip().upper()
    if not normalised.startswith("SELECT") and not normalised.startswith("WITH"):
        raise ValueError(
            "SQL must start with SELECT or WITH (CTEs). "
            f"Got: {sql[:80]!r}"
        )


def _run_query(sql: str) -> list[dict[str, Any]]:
    """Execute a validated SELECT statement and return rows as dicts."""
    conn: sqlite3.Connection = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _extract_table_names(sql: str) -> list[str]:
    """Heuristically extract table/view names referenced in a SQL statement."""
    # Match FROM and JOIN clauses.
    pattern = re.compile(
        r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        re.IGNORECASE,
    )
    names = pattern.findall(sql)
    return list(dict.fromkeys(names))  # deduplicate while preserving order


def _build_sources(sql: str, results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build a sources list from table names and any source_url values in results."""
    table_names = _extract_table_names(sql)
    seen_urls: set[str] = set()
    sources: list[dict[str, str]] = []

    # Pull source_url values from result rows (up to 5 unique URLs).
    for row in results[:MAX_RESULT_ROWS]:
        url = row.get("source_url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append({"table": "result_row", "source_url": url})
        if len(seen_urls) >= 5:
            break

    # Add fallback URLs from the static table map.
    for name in table_names:
        fallback = _TABLE_SOURCES.get(name)
        if fallback and fallback not in seen_urls:
            seen_urls.add(fallback)
            sources.append({"table": name, "source_url": fallback})

    return sources


def _build_sql_prompt(question: str) -> str:
    return textwrap.dedent(f"""
        You are a SQL expert working with a government transparency database for India.
        Your job is to write a single, correct SQLite SELECT statement that answers
        the user's question.

        DATABASE SCHEMA:
        {_SCHEMA_SUMMARY}

        RULES:
        1. Write ONLY a SELECT statement. No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE.
        2. Use UPPER CASE for all string literals that match state or district names.
        3. Prefer the unified views (scheme_finance, scheme_delivery, money_flow) for
           cross-scheme comparisons; use raw tables for scheme-specific detail.
        4. Always include source_url in the SELECT if available in the table.
        5. Add LIMIT 50 unless the question asks for a full dataset.
        6. Output only the SQL — no explanation, no markdown prose, no preamble.
           You may wrap it in a ```sql``` code block.

        USER QUESTION:
        {question}

        SQL:
    """).strip()


def _build_narrative_prompt(
    question: str,
    sql: str,
    results: list[dict[str, Any]],
    truncated: bool,
) -> str:
    results_text = _format_results_for_prompt(results)
    truncation_note = (
        f"\n[NOTE: Results were truncated to {MAX_RESULT_ROWS} rows for this summary.]"
        if truncated
        else ""
    )
    return textwrap.dedent(f"""
        You are an investigative journalist assistant analysing Indian government welfare data.
        Answer the user's question based ONLY on the query results below.
        Every numeric claim must be cited with the table name or source URL from the results.

        QUESTION:
        {question}

        SQL USED:
        {sql}

        QUERY RESULTS:{truncation_note}
        {results_text}

        INSTRUCTIONS:
        - Write a clear, factual narrative of 2–5 paragraphs.
        - Highlight the most significant findings (highest/lowest values, anomalies).
        - Cite the source table or URL next to each key number, e.g. "(source: misappropriation table)".
        - If the results are empty, say so clearly and suggest why the data may be missing.
        - Do NOT invent numbers not present in the results.
        - Do NOT mention the SQL itself in your narrative.

        NARRATIVE:
    """).strip()


def _format_results_for_prompt(results: list[dict[str, Any]]) -> str:
    if not results:
        return "(no rows returned)"
    if len(results) == 1:
        return "\n".join(f"  {k}: {v}" for k, v in results[0].items())

    # For multiple rows, format as a compact table.
    headers = list(results[0].keys())
    rows = [[str(row.get(h, "")) for h in headers] for row in results]
    col_widths = [
        max(len(h), max((len(r[i]) for r in rows), default=0))
        for i, h in enumerate(headers)
    ]
    sep = "  ".join("-" * w for w in col_widths)
    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    data_lines = [
        "  ".join(row[i].ljust(col_widths[i]) for i in range(len(headers)))
        for row in rows
    ]
    return "\n".join(["  " + header_line, "  " + sep] + ["  " + line for line in data_lines])


def investigate(
    question: str,
    api_key: str,
    provider: Provider,
    model: str | None = None,
) -> InvestigationResult:
    """Run a full investigation: NL question → SQL → results → narrative.

    Args:
        question: The user's natural language question about welfare scheme data.
        api_key:  The user's LLM provider API key. Never stored or returned.
        provider: LLM provider — "gemini", "openai", "groq", or "together".
        model:    Optional model override. Defaults to PROVIDER_DEFAULTS[provider].

    Returns:
        InvestigationResult with question, sql, results, narrative, and sources.

    Raises:
        ValueError: If the LLM generates an unsafe SQL statement.
        ImportError: If the required LLM package is not installed.
    """
    from llm.providers import PROVIDER_DEFAULTS

    resolved_model = model or PROVIDER_DEFAULTS.get(provider, "unknown")

    # Step 1 — generate SQL.
    sql_prompt = _build_sql_prompt(question)
    raw_sql_response = generate(sql_prompt, api_key=api_key, provider=provider, model=model)
    sql = _extract_sql(raw_sql_response)

    # Step 2 — validate (raises ValueError on mutation).
    _validate_sql(sql)

    # Step 3 — execute.
    all_results = _run_query(sql)
    truncated = len(all_results) > MAX_RESULT_ROWS
    results_for_narrative = all_results[:MAX_RESULT_ROWS]

    # Step 4 — generate narrative.
    narrative_prompt = _build_narrative_prompt(
        question, sql, results_for_narrative, truncated
    )
    narrative = generate(narrative_prompt, api_key=api_key, provider=provider, model=model)

    # Step 5 — build sources.
    sources = _build_sources(sql, results_for_narrative)

    return InvestigationResult(
        question=question,
        sql=sql,
        results=all_results,
        narrative=narrative.strip(),
        sources=sources,
        provider_used=provider,
        model_used=resolved_model,
        truncated=truncated,
    )

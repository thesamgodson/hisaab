"""Audited metric catalog for neutral temporal snapshots."""

from __future__ import annotations

MetricSpec = tuple[str, str, str | None, str, str, str, str]

METRIC_SPECS: tuple[MetricSpec, ...] = (
    ("MGNREGA", "financial_statement", "district", "state", "fin_year", "utilization_pct", "utilization_pct"),
    (
        "MGNREGA",
        "financial_statement",
        "district",
        "state",
        "fin_year",
        "cumulative_expenditure_lakhs",
        "cumulative_expenditure",
    ),
    ("MGNREGA", "misappropriation", "district", "state", "fin_year", "amount_unrecovered_rupees", "amount_unrecovered"),
    ("PMGSY", "pmgsy_district", "district", "state", "fin_year", "roads_completed", "roads_completed"),
    ("PMGSY", "pmgsy_district", "district", "state", "fin_year", "expenditure_cr", "expenditure_cr"),
    ("PMAY-G", "pmayg_district", "district", "state", "fin_year", "completion_pct", "completion_pct"),
    ("PMAY-G", "pmayg_district", "district", "state", "fin_year", "houses_completed", "houses_completed"),
    ("JJM", "jjm_district", "district", "state", "fin_year", "coverage_pct", "coverage_pct"),
    ("JJM", "jjm_district", "district", "state", "fin_year", "households_with_tap", "households_with_tap"),
    ("PM POSHAN", "pmposhan_district", "district", "state", "fin_year", "children_fed", "children_fed"),
    ("SBM-G", "sbm_district", "district", "state", "fin_year", "odf_plus_pct", "odf_plus_pct"),
    ("DAY-NRLM", "nrlm_district", "district", "state", "fin_year", "shgs_total", "shgs_total"),
    ("DAY-NRLM", "nrlm_district", "district", "state", "fin_year", "rf_amount_lakhs", "rf_amount_lakhs"),
    ("PMAY-G", "pmayg_finance", None, "state", "fin_year", "utilized_lakhs", "utilized_lakhs"),
    ("PM POSHAN", "pmposhan_finance", None, "state", "fin_year", "utilized_lakhs", "utilized_lakhs"),
    ("NSAP", "nsap_finance", None, "state", "fin_year", "released_lakhs", "released_lakhs"),
    ("JJM", "jjm_allocation", None, "state", "fin_year", "expended_crores", "expended_crores"),
)

_UNITS = {
    ("MGNREGA", "utilization_pct"): "%",
    ("MGNREGA", "cumulative_expenditure_lakhs"): "INR lakh",
    ("MGNREGA", "amount_unrecovered_rupees"): "INR rupee",
    ("PMGSY", "roads_completed"): "count",
    ("PMGSY", "expenditure_cr"): "INR crore",
    ("PMAY-G", "completion_pct"): "%",
    ("PMAY-G", "houses_completed"): "count",
    ("PMAY-G", "utilized_lakhs"): "INR lakh",
    ("JJM", "coverage_pct"): "%",
    ("JJM", "households_with_tap"): "count",
    ("JJM", "expended_crores"): "INR crore",
    ("PM POSHAN", "children_fed"): "count",
    ("PM POSHAN", "utilized_lakhs"): "INR lakh",
    ("NSAP", "released_lakhs"): "INR lakh",
    ("SBM-G", "odf_plus_pct"): "%",
    ("DAY-NRLM", "shgs_total"): "count",
    ("DAY-NRLM", "rf_amount_lakhs"): "INR lakh",
}

_NOTES = {
    ("PM POSHAN", "children_fed"): "Daily reporting count; not a coverage or utilization rate.",
    ("MGNREGA", "amount_unrecovered_rupees"): "Frozen FY2024-25 social-audit amount in rupees.",
}


def is_audited_metric(scheme: str, metric_name: str) -> bool:
    return (scheme, metric_name) in _UNITS


def audited_metric_names(scheme: str) -> set[str]:
    return {metric for (name, metric) in _UNITS if name.upper() == scheme.upper()}


def metric_context(scheme: str, metric_name: str) -> dict[str, str | None]:
    return {
        "unit": _UNITS.get((scheme, metric_name)),
        "metric_note": _NOTES.get((scheme, metric_name)),
        "direction_judgment": "not_audited",
    }

"""Query layer for multi-scheme government transparency data.

Schemes: MGNREGA, PMGSY, PMAY-G, PM Kisan, JJM, PM POSHAN, NSAP, PDS/NFSA.

Cross-scheme queries use the unified money_flow VIEW.

Each function returns a dict with 'answer' (human-readable), 'data' (raw), and 'source_url'.
"""

from queries.common import (
    data_quality_warnings,
    list_districts,
)
from queries.cross_scheme import (
    money_flow_by_district,
    money_flow_state_summary,
    schemes_in_district,
)
from queries.mgnrega import (
    district_overview,
    fto_pendency_summary,
    fto_status_by_district,
    fund_utilization_by_district,
    fund_utilization_state_summary,
    misappropriation_by_district,
    misappropriation_state_summary,
    social_audit_by_district,
    worst_misappropriation_districts,
)
from queries.other_schemes import (
    jjm_by_district,
    jjm_state_summary,
    jjm_worst_coverage,
    pmayg_by_district,
    pmayg_state_summary,
    pmayg_worst_completion,
    pmkisan_by_district,
    pmkisan_state_summary,
    pmkisan_worst_coverage,
)
from queries.pmgsy import (
    pmgsy_district_summary,
    pmgsy_state_summary,
    pmgsy_worst_completion,
)
from queries.trends import (
    district_trend,
    trending_better,
    trending_worse,
)
from queries.welfare_schemes import (
    nfsa_by_district,
    nfsa_state_summary,
    nfsa_worst_coverage,
    nsap_by_district,
    nsap_state_summary,
    nsap_worst_coverage,
    pmposhan_by_district,
    pmposhan_state_summary,
    pmposhan_worst_feeding,
)

__all__ = [
    "data_quality_warnings",
    "district_overview",
    "district_trend",
    "trending_better",
    "trending_worse",
    "fto_pendency_summary",
    "fto_status_by_district",
    "fund_utilization_by_district",
    "fund_utilization_state_summary",
    "jjm_by_district",
    "jjm_state_summary",
    "jjm_worst_coverage",
    "list_districts",
    "misappropriation_by_district",
    "misappropriation_state_summary",
    "money_flow_by_district",
    "money_flow_state_summary",
    "nfsa_by_district",
    "nfsa_state_summary",
    "nfsa_worst_coverage",
    "nsap_by_district",
    "nsap_state_summary",
    "nsap_worst_coverage",
    "pmayg_by_district",
    "pmayg_state_summary",
    "pmayg_worst_completion",
    "pmgsy_district_summary",
    "pmgsy_state_summary",
    "pmgsy_worst_completion",
    "pmkisan_by_district",
    "pmkisan_state_summary",
    "pmkisan_worst_coverage",
    "pmposhan_by_district",
    "pmposhan_state_summary",
    "pmposhan_worst_feeding",
    "schemes_in_district",
    "social_audit_by_district",
    "worst_misappropriation_districts",
]

"""Test that all project modules import cleanly without errors.

Parametrized over every importable module in the project so a broken
import fails fast with a clear error message rather than a confusing
AttributeError deep inside some other test.
"""

from __future__ import annotations

import importlib

import pytest

# All importable modules in the project (no .venv, no scraper scripts at root level —
# those are standalone scripts, not part of the package hierarchy).
_MODULES = [
    # db package
    "db",
    "db.connection",
    "db.schema",
    "db.loaders",
    "db.snapshots",
    # queries package
    "queries",
    "queries.common",
    "queries.composite",
    "queries.cross_scheme",
    "queries.mgnrega",
    "queries.other_schemes",
    "queries.pmgsy",
    "queries.trends",
    "queries.welfare_schemes",
    # api package
    "api",
    "api.main",
    "api.routes.constituency",
    "api.routes.district",
    "api.routes.embed",
    "api.routes.freshness",
    "api.routes.investigate",
    "api.routes.nl_query",
    "api.routes.schemes",
    "api.routes.scores",
    # llm package
    "llm",
    "llm.investigator",
    "llm.providers",
    # briefs package
    "briefs",
    # alerts package
    "alerts",
    "alerts.digest",
    "alerts.email_digest",
    # constituency package
    "constituency",
    "constituency.mapper",
    "constituency.report_card",
    "constituency.seed_data",
    # top-level modules
    "query",
]


@pytest.mark.parametrize("module_name", _MODULES)
def test_module_imports_cleanly(module_name: str) -> None:
    """Each module must importable without raising any exception."""
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        # Allow optional third-party deps (google-generativeai, openai, resend)
        # to be absent — those are only needed at runtime, not at import.
        optional_deps = {"google", "openai", "resend"}
        missing = str(exc).split("'")[1] if "'" in str(exc) else str(exc)
        if any(dep in missing for dep in optional_deps):
            pytest.skip(f"Optional dependency missing: {exc}")
        raise

"""Weekly alert transport with unaudited judgments fail-closed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DistrictChange:
    """A single district metric change entry."""

    district: str
    state: str
    scheme: str
    metric_name: str
    delta_pct: float
    prior_value: float | None
    current_value: float | None


@dataclass
class RedFlagEntry:
    """Compatibility shape for a future audited score-crossing event."""

    district: str
    state: str
    score: float
    grade: str
    flags: list[str]


@dataclass
class WeeklyDigest:
    """Container for the weekly accountability digest."""

    top_degrading: list[DistrictChange]
    top_improving: list[DistrictChange]
    new_red_flags: list[RedFlagEntry]
    headline: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    weeks: int = 1
    has_data: bool = True
    trend_judgments_suspended: bool = True
    red_flag_crossings_suspended: bool = True


# ---------------------------------------------------------------------------
# Headline builder
# ---------------------------------------------------------------------------


def _build_headline(
    degrading: list[DistrictChange],
    improving: list[DistrictChange],
    red_flags: list[RedFlagEntry],
) -> str:
    """Auto-generate a one-liner summary from digest contents."""
    if not degrading and not improving and not red_flags:
        return "Trend judgments and new-red-flag alerts are suspended pending audited contracts."

    parts: list[str] = []

    changes = [*degrading, *improving]
    if changes:
        scheme_counts: dict[str, int] = {}
        for d in changes:
            scheme_counts[d.scheme] = scheme_counts.get(d.scheme, 0) + 1
        top_scheme = max(scheme_counts, key=lambda s: scheme_counts[s])
        count = scheme_counts[top_scheme]
        noun = "district" if count == 1 else "districts"
        parts.append(f"{top_scheme} metrics changed in {count} {noun}; direction not judged")

    if red_flags:
        noun = "district" if len(red_flags) == 1 else "districts"
        parts.append(f"{len(red_flags)} {noun} with red-flag records listed; no new crossing inferred")

    joined = "; ".join(parts)
    return joined[0].upper() + joined[1:] + "." if joined else "."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_weekly_digest(
    weeks: int = 1,
    top_degrading_n: int = 10,
    top_improving_n: int = 5,
    red_flag_score_threshold: float = 40.0,
    db_path: Path | None = None,
) -> WeeklyDigest:
    """Generate red-flag alerts with unaudited trend judgments suspended.

    Args:
        weeks: How many weeks back to look for changes.
        top_degrading_n: Reserved until metric polarity is audited.
        top_improving_n: Reserved until metric polarity is audited.
        red_flag_score_threshold: Reserved until score crossings are audited.
        db_path: Reserved for the future audited comparisons.

    Returns:
        A populated WeeklyDigest instance.
    """
    # Field names remain for transport compatibility. They must stay empty
    # until polarity and score-crossing contracts are audited and registered.
    degrading: list[DistrictChange] = []
    improving: list[DistrictChange] = []
    red_flags: list[RedFlagEntry] = []

    has_data = bool(degrading or improving or red_flags)
    headline = _build_headline(degrading, improving, red_flags)

    return WeeklyDigest(
        top_degrading=degrading,
        top_improving=improving,
        new_red_flags=red_flags,
        headline=headline,
        generated_at=datetime.now(UTC),
        weeks=weeks,
        has_data=has_data,
    )

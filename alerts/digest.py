"""Weekly digest generation for Hisaab accountability alerts.

Pulls trend data from the metrics_snapshot table and composite scores from
queries/composite.py to produce a WeeklyDigest dataclass ready for delivery
via Telegram or email.
"""

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
    """A district that crossed a red flag threshold."""

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
        return "No significant changes detected this week."

    parts: list[str] = []

    if degrading:
        # Group by scheme to find the busiest scheme
        scheme_counts: dict[str, int] = {}
        for d in degrading:
            scheme_counts[d.scheme] = scheme_counts.get(d.scheme, 0) + 1
        top_scheme = max(scheme_counts, key=lambda s: scheme_counts[s])
        count = scheme_counts[top_scheme]
        noun = "district" if count == 1 else "districts"
        parts.append(f"{top_scheme} metrics degraded in {count} {noun}")

    if red_flags:
        noun = "district" if len(red_flags) == 1 else "districts"
        parts.append(f"{len(red_flags)} {noun} crossed red-flag thresholds")

    if improving and not parts:
        count = len(improving)
        noun = "district" if count == 1 else "districts"
        parts.append(f"{count} {noun} showed improvement this week")

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
    """Generate the weekly accountability digest.

    Pulls degrading and improving districts from trend data and identifies
    districts whose composite score has fallen below the red flag threshold.

    Args:
        weeks: How many weeks back to look for changes.
        top_degrading_n: How many degrading districts to include.
        top_improving_n: How many improving districts to include.
        red_flag_score_threshold: Districts scoring below this are red flags.
        db_path: Optional path to SQLite database (defaults to DB_PATH).

    Returns:
        A populated WeeklyDigest instance.
    """
    from queries.composite import compute_district_scores
    from queries.trends import trending_better, trending_worse

    # --- Degrading districts ---
    worse_result = trending_worse(n=top_degrading_n, weeks=weeks, db_path=db_path)
    degrading: list[DistrictChange] = [
        DistrictChange(
            district=item["district"],
            state=item["state"],
            scheme=item["scheme"],
            metric_name=item["metric_name"],
            delta_pct=item["delta_pct"],
            prior_value=item.get("prior_value"),
            current_value=item.get("current_value"),
        )
        for item in worse_result.get("data", [])
    ]

    # --- Improving districts ---
    better_result = trending_better(n=top_improving_n, weeks=weeks, db_path=db_path)
    improving: list[DistrictChange] = [
        DistrictChange(
            district=item["district"],
            state=item["state"],
            scheme=item["scheme"],
            metric_name=item["metric_name"],
            delta_pct=item["delta_pct"],
            prior_value=item.get("prior_value"),
            current_value=item.get("current_value"),
        )
        for item in better_result.get("data", [])
    ]

    # --- Red flags: districts with composite score below threshold ---
    red_flags: list[RedFlagEntry] = []
    try:
        all_scores = compute_district_scores()
        for record in all_scores:
            score = record.get("score")
            if score is not None and score < red_flag_score_threshold and record.get("red_flags"):
                red_flags.append(
                    RedFlagEntry(
                        district=record["district"],
                        state=record["state"],
                        score=score,
                        grade=record.get("grade", "F"),
                        flags=record.get("red_flags", []),
                    )
                )
    except Exception:
        # DB may be empty — graceful degradation
        pass

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

"""Constituency package — PIN → District → Constituency → MP Report Card.

Public API:
    pin_to_district(pin_code)          -> dict | None
    district_to_constituency(district, state) -> list[dict]
    get_mp_info(constituency)          -> dict | None
    generate_mp_report_card(constituency) -> MPReportCard
    generate_report_card_image(report_card) -> bytes
    load_constituency_data(records)    -> int  (seed helper)
"""

from __future__ import annotations

from constituency.mapper import (
    district_to_constituency,
    get_mp_info,
    load_constituency_data,
    pin_to_district,
)
from constituency.report_card import MPReportCard, generate_mp_report_card, generate_report_card_image

__all__ = [
    "MPReportCard",
    "district_to_constituency",
    "generate_mp_report_card",
    "generate_report_card_image",
    "get_mp_info",
    "load_constituency_data",
    "pin_to_district",
]

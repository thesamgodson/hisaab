"""Frozen dataclasses for the citizen action brief."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class DiagnosisItem:
    severity: str          # "high", "medium", "low"
    scheme: str
    summary: str
    detail: str
    amount: str | None
    source_url: str


@dataclass(frozen=True)
class ContactCard:
    role: str
    name: str | None
    phone: str | None
    email: str | None
    office_address: str | None
    relevance: str
    source_url: str
    last_verified: date
    freshness: str         # "fresh", "stale", "expired"


@dataclass(frozen=True)
class ActionItem:
    scheme: str
    action: str
    portal_name: str
    portal_url: str
    source_url: str
    verified_at: str
    escalation: str | None = None
    escalation_url: str | None = None


@dataclass(frozen=True)
class ActionBrief:
    pin: str
    district: str
    state: str
    mp: dict[str, Any] | None
    mla: dict[str, Any] | None
    diagnosis: list[DiagnosisItem]
    contacts: list[ContactCard]
    actions: list[ActionItem]
    scheme_data: dict[str, Any]
    generated_at: datetime
    # Empty until a registered load-time diagnosis contract exists.
    schemes_checked: list[str] = field(default_factory=list)
    # Every curated complaint family, independent of district performance-data
    # coverage. Twin of complaint_kits/universal_channels in action-types.ts.
    complaint_kits: list[dict[str, Any]] = field(default_factory=list)
    universal_channels: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class DistrictBrief:
    """District-grain brief — the same sections as ActionBrief with honestly
    PLURAL representatives (a district commonly spans 2-3 Lok Sabha seats).
    Twin of DistrictBriefResponse in web/src/lib/action-brief.ts."""

    district: str
    state: str
    formerly_part_of: dict[str, Any] | None
    mps: list[dict[str, Any]]
    ac_count: int
    diagnosis: list[DiagnosisItem]
    schemes_checked: list[str]
    complaint_kits: list[dict[str, Any]]
    universal_channels: list[dict[str, Any]]
    generated_at: datetime

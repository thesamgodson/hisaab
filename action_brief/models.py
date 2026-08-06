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
    escalation: str
    escalation_url: str


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
    # Schemes that reported district data at all — an empty diagnosis with an
    # empty list means "nothing was checked", not "nothing is wrong".
    schemes_checked: list[str] = field(default_factory=list)

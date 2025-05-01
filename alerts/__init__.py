"""Hisaab alerts package — weekly digest generation, Telegram bot, and email delivery."""

from __future__ import annotations

from alerts.digest import WeeklyDigest, generate_weekly_digest

__all__ = [
    "WeeklyDigest",
    "generate_weekly_digest",
]

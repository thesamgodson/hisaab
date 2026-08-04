"""Telegram bot for Hisaab accountability alerts.

Bot commands:
  /start          — welcome message + subscribe to daily alerts
  /district NAME  — current accountability snapshot for a district
  /worst          — today's worst 5 districts
  /redflags       — current red flags
  /subscribe STATE — subscribe to alerts for a specific state
  /unsubscribe    — stop all alerts

Bot token comes from the HISAAB_TELEGRAM_TOKEN environment variable.
Subscriber state is persisted in the telegram_subscribers SQLite table.

Requires: python-telegram-bot>=21.0 (optional dependency).
"""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful import of optional dependency
# ---------------------------------------------------------------------------

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False
    logger.warning(
        "python-telegram-bot is not installed. "
        "Install it with: pip install python-telegram-bot>=21.0"
    )

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_db_conn(db_path: Path | None = None) -> sqlite3.Connection:
    from db.connection import DB_PATH, get_connection
    return get_connection(db_path or DB_PATH)


def _add_subscriber(
    chat_id: int,
    username: str | None,
    subscribed_states: str = "ALL",
    db_path: Path | None = None,
) -> None:
    conn = _get_db_conn(db_path)
    try:
        conn.execute(
            """
            INSERT INTO telegram_subscribers (chat_id, username, subscribed_states, active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(chat_id) DO UPDATE SET
                active = 1,
                subscribed_states = excluded.subscribed_states,
                username = excluded.username
            """,
            (chat_id, username, subscribed_states),
        )
        conn.commit()
    finally:
        conn.close()


def _remove_subscriber(chat_id: int, db_path: Path | None = None) -> None:
    conn = _get_db_conn(db_path)
    try:
        conn.execute(
            "UPDATE telegram_subscribers SET active = 0 WHERE chat_id = ?",
            (chat_id,),
        )
        conn.commit()
    finally:
        conn.close()


def _get_active_subscribers(db_path: Path | None = None) -> list[dict[str, Any]]:
    conn = _get_db_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT chat_id, username, subscribed_states FROM telegram_subscribers WHERE active = 1"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Message formatters
# ---------------------------------------------------------------------------

def _format_district_snapshot(district: str) -> str:
    """Return a short accountability snapshot for a district."""
    try:
        # Attempt to find the state by scanning composite scores
        from queries.composite import compute_district_scores
        all_scores = compute_district_scores()
        match = next(
            (r for r in all_scores if r["district"].upper() == district.upper()),
            None,
        )
        if not match:
            return f"No data found for district: {district.upper()}"

        score = match.get("score")
        grade = match.get("grade", "N/A")
        flags = match.get("red_flags", [])
        schemes = match.get("schemes_with_data", [])

        lines = [
            f"*{match['district']}, {match['state']}*",
            f"Score: {score:.1f}/100 (Grade {grade})" if score is not None else "Score: N/A",
            f"Schemes: {', '.join(schemes) if schemes else 'None'}",
        ]
        if flags:
            lines.append("⚠️ Red flags:")
            for flag in flags[:3]:
                lines.append(f"  • {flag}")
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Error fetching district snapshot: %s", exc)
        return f"Error fetching data for {district}."


def _format_worst_districts(n: int = 5) -> str:
    """Return the bottom N districts by composite score."""
    try:
        from queries.composite import get_worst_districts
        worst = get_worst_districts(n=n)
        if not worst:
            return "No scored districts found in the database."
        lines = [f"*Worst {n} districts (composite score):*"]
        for i, rec in enumerate(worst, 1):
            score = rec.get("score")
            score_str = f"{score:.1f}" if score is not None else "N/A"
            lines.append(f"{i}. {rec['district']}, {rec['state']} — {score_str}/100 (Grade {rec.get('grade', '?')})")
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Error fetching worst districts: %s", exc)
        return "Error fetching worst districts."


def _format_red_flags() -> str:
    """Return districts with the most severe red flags."""
    try:
        from queries.composite import compute_district_scores
        all_scores = compute_district_scores()
        flagged = [r for r in all_scores if r.get("red_flags") and r.get("score", 100) < 40]
        if not flagged:
            return "No active red flags found."
        lines = [f"*Red flags ({len(flagged)} districts):*"]
        for rec in flagged[:10]:
            score = rec.get("score")
            score_str = f"{score:.1f}" if score is not None else "N/A"
            flags_summary = "; ".join(rec["red_flags"][:2])
            lines.append(f"• *{rec['district']}, {rec['state']}* ({score_str}) — {flags_summary}")
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Error fetching red flags: %s", exc)
        return "Error fetching red flags."


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None
    _add_subscriber(chat_id, username)
    await update.message.reply_text(
        "👁️ *Hisaab Watchdog* — Government Accountability Bot\n\n"
        "You are now subscribed to daily alerts.\n\n"
        "Commands:\n"
        "/district NAME — accountability snapshot\n"
        "/worst — worst 5 districts today\n"
        "/redflags — active red flags\n"
        "/subscribe STATE — alerts for a state\n"
        "/unsubscribe — stop alerts",
        parse_mode="Markdown",
    )


async def _cmd_district(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /district <district name>")
        return
    district = " ".join(context.args)
    text = _format_district_snapshot(district)
    await update.message.reply_text(text, parse_mode="Markdown")


async def _cmd_worst(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = _format_worst_districts(n=5)
    await update.message.reply_text(text, parse_mode="Markdown")


async def _cmd_redflags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = _format_red_flags()
    await update.message.reply_text(text, parse_mode="Markdown")


async def _cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    username = update.effective_user.username if update.effective_user else None
    if not context.args:
        await update.message.reply_text("Usage: /subscribe <STATE NAME> (or ALL for all states)")
        return
    state = " ".join(context.args).upper()
    _add_subscriber(chat_id, username, subscribed_states=state)
    await update.message.reply_text(
        f"Subscribed to alerts for: *{state}*",
        parse_mode="Markdown",
    )


async def _cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _remove_subscriber(chat_id)
    await update.message.reply_text("You have been unsubscribed from Hisaab alerts.")


# ---------------------------------------------------------------------------
# Digest sender
# ---------------------------------------------------------------------------

def _format_digest_message(digest: Any) -> str:
    """Format a WeeklyDigest into a Telegram Markdown message."""
    lines = [
        "📊 *Hisaab Weekly Digest*",
        "",
        f"_{digest.headline}_",
        "",
    ]

    if digest.top_degrading:
        lines.append(f"*Degrading ({len(digest.top_degrading)} districts):*")
        for item in digest.top_degrading[:5]:
            delta_str = f"{item.delta_pct:.1f}%"
            lines.append(
                f"• {item.district}, {item.state} — {item.scheme} {item.metric_name} {delta_str}"
            )
        lines.append("")

    if digest.top_improving:
        lines.append(f"*Improving ({len(digest.top_improving)} districts):*")
        for item in digest.top_improving[:5]:
            delta_str = f"+{item.delta_pct:.1f}%"
            lines.append(
                f"• {item.district}, {item.state} — {item.scheme} {item.metric_name} {delta_str}"
            )
        lines.append("")

    if digest.new_red_flags:
        lines.append(f"*Red Flags ({len(digest.new_red_flags)} districts):*")
        for entry in digest.new_red_flags[:5]:
            flags_str = "; ".join(entry.flags[:2])
            lines.append(f"• {entry.district}, {entry.state} (score {entry.score:.0f}) — {flags_str}")

    return "\n".join(lines)


async def send_daily_digest(
    bot_token: str,
    digest: Any,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Send the weekly digest to all active subscribers.

    Args:
        bot_token: Telegram bot token.
        digest: A WeeklyDigest instance.
        db_path: Optional path to the SQLite database.

    Returns:
        dict with 'sent', 'failed', and 'skipped' counts.
    """
    if not _TELEGRAM_AVAILABLE:
        return {"error": "python-telegram-bot not installed", "sent": 0, "failed": 0}

    from telegram import Bot

    if not digest.has_data:
        return {"sent": 0, "failed": 0, "skipped": "no_data"}

    subscribers = _get_active_subscribers(db_path)
    if not subscribers:
        return {"sent": 0, "failed": 0, "skipped": "no_subscribers"}

    message = _format_digest_message(digest)
    bot = Bot(token=bot_token)

    sent = 0
    failed = 0
    for sub in subscribers:
        try:
            await bot.send_message(
                chat_id=sub["chat_id"],
                text=message,
                parse_mode="Markdown",
            )
            sent += 1
        except Exception as exc:
            logger.warning("Failed to send to chat_id %s: %s", sub["chat_id"], exc)
            failed += 1

    return {"sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# Bot runner
# ---------------------------------------------------------------------------

def run_bot(db_path: Path | None = None) -> None:
    """Start the Telegram bot in polling mode.

    Reads the bot token from HISAAB_TELEGRAM_TOKEN env var.
    Blocks until interrupted.
    """
    if not _TELEGRAM_AVAILABLE:
        raise ImportError(
            "python-telegram-bot is required. Install with: pip install python-telegram-bot>=21.0"
        )

    token = os.environ.get("HISAAB_TELEGRAM_TOKEN")
    if not token:
        raise ValueError("HISAAB_TELEGRAM_TOKEN environment variable is not set.")

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    app.add_handler(CommandHandler("start", _cmd_start))
    app.add_handler(CommandHandler("district", _cmd_district))
    app.add_handler(CommandHandler("worst", _cmd_worst))
    app.add_handler(CommandHandler("redflags", _cmd_redflags))
    app.add_handler(CommandHandler("subscribe", _cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", _cmd_unsubscribe))

    logger.info("Hisaab Telegram bot starting in polling mode…")
    app.run_polling()

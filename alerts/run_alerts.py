"""CLI entry point for Hisaab alert delivery.

Usage:
  python -m alerts.run_alerts --telegram          # Send Telegram digest to all subscribers
  python -m alerts.run_alerts --email recipients.txt  # Send email digest
  python -m alerts.run_alerts --preview           # Print digest to stdout (no sending)

Environment variables:
  HISAAB_TELEGRAM_TOKEN   — Telegram bot token
  HISAAB_RESEND_KEY       — Resend API key (email, preferred)
  HISAAB_SMTP_HOST/PORT/USER/PASSWORD/FROM — SMTP fallback credentials
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Preview formatter (stdout)
# ---------------------------------------------------------------------------

def _print_digest_preview(digest: object) -> None:
    """Print a human-readable digest to stdout."""
    from alerts.email_digest import _render_plaintext
    print(_render_plaintext(digest))  # noqa: T201


# ---------------------------------------------------------------------------
# Telegram delivery
# ---------------------------------------------------------------------------

async def _run_telegram(digest: object) -> None:
    token = os.environ.get("HISAAB_TELEGRAM_TOKEN")
    if not token:
        logger.error("HISAAB_TELEGRAM_TOKEN environment variable is not set.")
        sys.exit(1)

    from alerts.telegram_bot import send_daily_digest
    result = await send_daily_digest(bot_token=token, digest=digest)
    logger.info("Telegram delivery: sent=%s failed=%s", result.get("sent"), result.get("failed"))
    if result.get("error"):
        logger.error("Telegram error: %s", result["error"])
        sys.exit(1)


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

def _run_email(digest: object, recipients_file: str) -> None:
    path = Path(recipients_file)
    if not path.exists():
        logger.error("Recipients file not found: %s", recipients_file)
        sys.exit(1)

    recipients = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not recipients:
        logger.error("No recipients found in %s", recipients_file)
        sys.exit(1)

    from alerts.email_digest import send_email_digest
    result = send_email_digest(recipients=recipients, digest=digest)
    logger.info(
        "Email delivery via %s: sent=%s failed=%s",
        result.get("backend"),
        len(result.get("sent", [])),
        len(result.get("failed", [])),
    )
    if result.get("failed"):
        for item in result["failed"]:
            logger.warning("Failed: %s — %s", item.get("recipient"), item.get("error"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Hisaab alert delivery — Telegram, email, or preview.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Send weekly digest to all Telegram subscribers.",
    )
    parser.add_argument(
        "--email",
        metavar="RECIPIENTS_FILE",
        help="Send weekly digest to addresses listed in RECIPIENTS_FILE (one per line).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print digest to stdout without sending anything.",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=1,
        help="Comparison window in weeks (default: 1).",
    )

    args = parser.parse_args(argv)

    if not any([args.telegram, args.email, args.preview]):
        parser.print_help()
        sys.exit(1)

    logger.info("Generating weekly digest (weeks=%d)…", args.weeks)
    from alerts.digest import generate_weekly_digest
    digest = generate_weekly_digest(weeks=args.weeks)
    logger.info("Digest ready: %s", digest.headline)

    if args.preview:
        _print_digest_preview(digest)

    if args.telegram:
        asyncio.run(_run_telegram(digest))

    if args.email:
        _run_email(digest, args.email)


if __name__ == "__main__":
    main()

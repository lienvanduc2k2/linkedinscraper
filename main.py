"""
Main entry point for LinkedIn Job Scraper → Telegram Bot.

Usage:
    python main.py                  # Run full pipeline (scrape + send)
    python main.py --dry-run        # Scrape only, don't send to Telegram
    python main.py --test-telegram  # Test Telegram connection only
    python main.py --force          # Send all jobs (ignore seen-jobs DB)
"""
import asyncio
import argparse
import os
import sys
import yaml
from dotenv import load_dotenv

from src.scraper.linkedin_scraper import run_scraper
from src.bot.telegram_bot import send_jobs_to_telegram, test_telegram_connection
from src.storage.job_store import JobStore
from src.utils.logger import log


def load_config(config_path: str = "config/config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def main(dry_run: bool = False, test_telegram: bool = False, force: bool = False):
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    topic_id_raw = os.getenv("TELEGRAM_TOPIC_ID")
    topic_id = int(topic_id_raw) if topic_id_raw else None

    if not bot_token or not chat_id:
        log.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env")
        sys.exit(1)

    # Test mode
    if test_telegram:
        log.info("Testing Telegram connection...")
        ok = await test_telegram_connection(bot_token, chat_id, topic_id)
        if ok:
            log.success("Telegram test passed!")
        else:
            log.error("Telegram test failed!")
        return

    config = load_config()
    telegram_cfg = config.get("telegram", {})

    # ── Step 1: Scrape LinkedIn ──
    log.info("=" * 50)
    log.info("🔍 Starting LinkedIn scrape...")
    log.info("=" * 50)
    all_jobs = await run_scraper(config)

    if not all_jobs:
        log.warning("No jobs found from LinkedIn. Check if LinkedIn blocked the scraper.")
        return

    # ── Step 2: Filter new jobs (not yet sent) ──
    store = JobStore()
    if force:
        new_jobs = all_jobs
        log.warning(f"--force mode: sending all {len(new_jobs)} jobs regardless of history")
    else:
        new_jobs = store.get_new_jobs(all_jobs)

    log.info(f"📋 New jobs to send: {len(new_jobs)}")
    if not new_jobs:
        log.info("No new jobs to send — skipping Telegram")
        return

    # ── Step 3: Print preview ──
    for i, job in enumerate(new_jobs[:5], 1):
        log.info(f"  [{i}] {job['title']} @ {job['company']} | {job['location']} | {job['posted_time']}")
    if len(new_jobs) > 5:
        log.info(f"  ... and {len(new_jobs) - 5} more")

    if dry_run:
        log.info("🚫 DRY RUN mode — skipping Telegram send")
        log.info(f"✅ Would send {len(new_jobs)} jobs")
        return

    # ── Step 4: Send to Telegram ──
    log.info("📤 Sending to Telegram...")
    sent = await send_jobs_to_telegram(
        jobs=new_jobs,
        bot_token=bot_token,
        chat_id=chat_id,
        topic_id=topic_id,
        max_per_batch=telegram_cfg.get("max_jobs_per_batch", 10),
        delay_seconds=telegram_cfg.get("delay_between_messages", 1),
    )

    # ── Step 5: Mark sent jobs in DB ──
    for job in new_jobs[:sent]:
        store.mark_sent(job)

    log.success(f"✅ Done! Sent {sent} jobs to Telegram.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn → Telegram Job Bot")
    parser.add_argument("--dry-run", action="store_true", help="Scrape only, don't send")
    parser.add_argument("--test-telegram", action="store_true", help="Test Telegram connection")
    parser.add_argument("--force", action="store_true", help="Send all jobs, ignore history")
    args = parser.parse_args()

    asyncio.run(main(
        dry_run=args.dry_run,
        test_telegram=args.test_telegram,
        force=args.force,
    ))

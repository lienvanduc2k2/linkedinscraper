"""
Scheduler — Chạy scraper tự động lúc 13:20 hàng ngày (giờ Việt Nam).
Usage: python scheduler.py
"""
import asyncio
import os
import sys
import yaml
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from src.scraper.linkedin_scraper import run_scraper
from src.bot.telegram_bot import send_jobs_to_telegram
from src.storage.job_store import JobStore
from src.utils.logger import log


def load_config(config_path: str = "config/config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def scrape_and_notify():
    """The main job that runs on schedule."""
    log.info("⏰ Scheduled job triggered!")
    load_dotenv()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        log.error("Missing Telegram credentials in .env")
        return

    config = load_config()
    telegram_cfg = config.get("telegram", {})

    try:
        # Scrape
        log.info("🔍 Scraping LinkedIn jobs...")
        all_jobs = await run_scraper(config)

        # Filter new
        store = JobStore()
        new_jobs = store.get_new_jobs(all_jobs)

        log.info(f"📋 {len(new_jobs)} new jobs to send")

        # Send
        sent = await send_jobs_to_telegram(
            jobs=new_jobs,
            bot_token=bot_token,
            chat_id=chat_id,
            max_per_batch=telegram_cfg.get("max_jobs_per_batch", 10),
            delay_seconds=telegram_cfg.get("delay_between_messages", 1),
        )

        # Mark as sent
        for job in new_jobs[:sent]:
            store.mark_sent(job)

        log.success(f"✅ Scheduled run complete. Sent {sent} jobs.")

    except Exception as e:
        log.error(f"Scheduled job failed: {e}")
        raise


def on_job_executed(event):
    log.info(f"✅ Job '{event.job_id}' executed successfully")


def on_job_error(event):
    log.error(f"❌ Job '{event.job_id}' failed: {event.exception}")


async def start_scheduler():
    load_dotenv()
    config = load_config()
    scheduler_cfg = config.get("scheduler", {})

    hour = scheduler_cfg.get("hour", 13)
    minute = scheduler_cfg.get("minute", 20)
    timezone = scheduler_cfg.get("timezone", "Asia/Ho_Chi_Minh")

    scheduler = AsyncIOScheduler(timezone=timezone)

    scheduler.add_listener(on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)

    scheduler.add_job(
        scrape_and_notify,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone),
        id="linkedin_scraper",
        name="LinkedIn Frontend Jobs Scraper",
        max_instances=1,
        misfire_grace_time=300,  # 5 minutes grace period
    )

    scheduler.start()

    jobs = scheduler.get_jobs()
    for job in jobs:
        next_run = job.next_run_time
        log.info(f"📅 Scheduled: '{job.name}'")
        log.info(f"   Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    log.info("=" * 50)
    log.info("🤖 LinkedIn Job Bot Scheduler is RUNNING")
    log.info(f"⏰ Will scrape at {hour:02d}:{minute:02d} {timezone} every day")
    log.info("   Press Ctrl+C to stop")
    log.info("=" * 50)

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped by user")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(start_scheduler())

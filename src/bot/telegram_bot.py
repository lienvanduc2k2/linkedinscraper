"""
Telegram Bot — Gửi thông báo việc làm Frontend Developer.
"""
import asyncio
import os
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from src.utils.logger import log


def format_job_message(job: dict, index: int, total: int) -> str:
    """Format a single job into a beautiful Telegram message."""
    title = job.get("title", "N/A")
    company = job.get("company", "N/A")
    location = job.get("location", "N/A")
    url = job.get("url", "#")
    posted = job.get("posted_time", "N/A")
    salary = job.get("salary")

    salary_line = f"💰 *Lương:* {salary}\n" if salary else ""

    message = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 *{title}*\n"
        f"🏢 {company}\n"
        f"📍 {location}\n"
        f"⏰ {posted}\n"
        f"{salary_line}"
        f"🔗 [Xem chi tiết]({url})\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return message


def format_header_message(job_count: int) -> str:
    """Format header message before sending jobs."""
    return (
        f"🚀 *LinkedIn Job Alert — Frontend Developer*\n"
        f"📅 Tìm thấy *{job_count} việc làm mới* trong 24h qua!\n"
        f"🎯 Junior Level \u2022 Onsite \u2022 Ho Chi Minh City\n"
    )


def format_footer_message() -> str:
    """Format footer message after all jobs."""
    return (
        "✅ *Đã gửi xong tất cả việc làm mới!*\n"
        "💡 Bot sẽ tự động cập nhật lúc *13:20* hàng ngày."
    )


async def send_jobs_to_telegram(
    jobs: list[dict],
    bot_token: str,
    chat_id: str,
    max_per_batch: int = 10,
    delay_seconds: float = 2.0,
) -> int:
    """Send job listings to Telegram. Returns number of successfully sent jobs."""
    if not jobs:
        log.info("No new jobs to send")
        await _send_no_jobs_message(bot_token, chat_id)
        return 0

    bot = Bot(token=bot_token)
    sent_count = 0

    try:
        # Send jobs in batches
        batch = jobs[:max_per_batch]
        for i, job in enumerate(batch):
            try:
                msg = format_job_message(job, i + 1, len(batch))
                await bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
                sent_count += 1
                log.debug(f"Sent job {i+1}/{len(batch)}: {job.get('title')} @ {job.get('company')}")
                await asyncio.sleep(delay_seconds)
            except TelegramError as e:
                log.error(f"Failed to send job {i+1} (markdown): {e}")
                # Try plain text fallback
                try:
                    plain = (
                        f"\U0001f4bc {job.get('title', 'N/A')} — {job.get('company', 'N/A')}\n"
                        f"\U0001f4cd {job.get('location', 'N/A')} | \u23f0 {job.get('posted_time', 'N/A')}\n"
                        f"\U0001f517 {job.get('url', '#')}"
                    )
                    await bot.send_message(chat_id=chat_id, text=plain)
                    sent_count += 1
                    await asyncio.sleep(delay_seconds)
                except Exception as e2:
                    log.error(f"Fallback also failed: {e2}")


    except TelegramError as e:
        log.error(f"Telegram error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

    log.success(f"Successfully sent {sent_count} jobs to Telegram")
    return sent_count


async def _send_no_jobs_message(bot_token: str, chat_id: str):
    """Send a message when no new jobs are found."""
    bot = Bot(token=bot_token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "📭 *Không có việc làm mới*\n"
                "Hôm nay chưa có Frontend Developer job mới nào trong 24h qua.\n"
                "Bot sẽ kiểm tra lại vào ngày mai lúc *13:20* ⏰"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        log.error(f"Failed to send 'no jobs' message: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass


async def test_telegram_connection(bot_token: str, chat_id: str) -> bool:
    """Test Telegram bot connection."""
    bot = Bot(token=bot_token)
    try:
        me = await bot.get_me()
        log.info(f"Bot connected: @{me.username} ({me.first_name})")
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "✅ *LinkedIn Job Bot — Kết nối thành công!*\n"
                "🤖 Bot đã sẵn sàng gửi thông báo việc làm Frontend Developer\n"
                "⏰ Lịch chạy: *13:20* hàng ngày (Giờ Việt Nam)"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
        return True
    except TelegramError as e:
        log.error(f"Telegram connection failed: {e}")
        return False
    finally:
        try:
            await bot.close()
        except Exception:
            pass

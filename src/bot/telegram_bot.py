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
    """Send all job listings in ONE combined Telegram message (auto-split if > 4096 chars)."""
    if not jobs:
        log.info("No new jobs to send")
        await _send_no_jobs_message(bot_token, chat_id)
        return 0

    bot = Bot(token=bot_token)
    sent_count = 0
    MAX_LEN = 4096

    try:
        display_jobs = jobs[:max_per_batch]
        total = len(display_jobs)

        # Build header
        header = format_header_message(total)

        # Build each job entry (compact format for combined message)
        job_lines = []
        for i, job in enumerate(display_jobs, 1):
            title = job.get("title", "N/A")
            company = job.get("company", "N/A")
            location = job.get("location", "N/A")
            posted = job.get("posted_time", "N/A")
            url = job.get("url", "#")
            salary = job.get("salary")

            salary_part = f" 💰 {salary}" if salary else ""
            line = (
                f"\n*{i}. {title}*\n"
                f"🏢 {company} • 📍 {location} • ⏰ {posted}{salary_part}\n"
                f"🔗 [Xem chi tiết]({url})"
            )
            job_lines.append(line)

        footer = f"\n\n✅ *Đã gửi xong {total} việc làm mới!*\n💡 Bot tự động cập nhật lúc *13:20* hàng ngày."

        # Pack jobs into chunks, respecting Telegram's 4096-char limit
        chunks = []
        current_chunk = header
        for line in job_lines:
            if len(current_chunk) + len(line) + len(footer) + 1 > MAX_LEN:
                chunks.append(current_chunk + footer)
                current_chunk = f"📋 *Tiếp theo ({len(chunks) + 1}):*"
            current_chunk += "\n" + line

        chunks.append(current_chunk + footer)

        # Send chunks
        for chunk_idx, chunk in enumerate(chunks):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
                sent_count = total
                log.debug(f"Sent chunk {chunk_idx + 1}/{len(chunks)}")
                if chunk_idx < len(chunks) - 1:
                    await asyncio.sleep(delay_seconds)
            except TelegramError as e:
                log.error(f"Failed to send chunk {chunk_idx + 1} (markdown): {e}")
                # Fallback: strip markdown
                try:
                    import re as _re
                    plain = _re.sub(r"[*_`\[\]()]", "", chunk)
                    await bot.send_message(
                        chat_id=chat_id,
                        text=plain,
                        disable_web_page_preview=True,
                    )
                    sent_count = total
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

    log.success(f"Successfully sent {sent_count} jobs to Telegram in {len(chunks) if jobs else 0} message(s)")
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

"""
Telegram Bot — Gửi thông báo việc làm Frontend Developer.
"""
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from src.utils.logger import log



def _format_job_line(index: int, job: dict) -> str:
    """Format một job theo đúng format yêu cầu."""
    title    = job.get("title", "N/A")
    company  = job.get("company", "N/A")
    location = job.get("location", "N/A")
    posted   = job.get("posted_time", "N/A")
    url      = job.get("url", "#")
    matched  = job.get("matched_keywords", [])

    lines = [
        f"{index}. {title}",
        f"🏢 {company} • 📍 {location} • ⏰ {posted}",
    ]
    if matched:
        lines.append(f"⚙️ {', '.join(matched[:6])}")
    lines.append(f"🔗 Xem chi tiết ({url})")

    return "\n".join(lines)


async def send_jobs_to_telegram(
    jobs: list[dict],
    bot_token: str,
    chat_id: str,
    topic_id: int | None = None,
    max_per_batch: int = 10,
    delay_seconds: float = 2.0,
) -> int:
    """Gửi danh sách job vào 1 message. Im lặng hoàn toàn nếu không có job."""
    if not jobs:
        log.info("No new jobs — skipping Telegram message")
        return 0

    bot = Bot(token=bot_token)
    sent_count = 0
    MAX_LEN = 4096

    try:
        display_jobs = jobs[:max_per_batch]
        total = len(display_jobs)

        # Build từng block job
        job_blocks = [_format_job_line(i, job) for i, job in enumerate(display_jobs, 1)]

        # Gộp thành chunks ≤ 4096 ký tự
        chunks: list[str] = []
        current = ""
        for block in job_blocks:
            separator = "\n\n" if current else ""
            if len(current) + len(separator) + len(block) > MAX_LEN:
                chunks.append(current)
                current = block
            else:
                current += separator + block
        if current:
            chunks.append(current)

        # Gửi từng chunk
        for idx, chunk in enumerate(chunks):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=topic_id,
                    text=chunk,
                    disable_web_page_preview=True,
                )
                sent_count = total
                log.debug(f"Sent chunk {idx + 1}/{len(chunks)}")
                if idx < len(chunks) - 1:
                    await asyncio.sleep(delay_seconds)
            except TelegramError as e:
                log.error(f"Failed to send chunk {idx + 1}: {e}")

    except TelegramError as e:
        log.error(f"Telegram error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

    log.success(f"Sent {sent_count} jobs in {len(chunks) if jobs else 0} message(s)")
    return sent_count


async def test_telegram_connection(bot_token: str, chat_id: str, topic_id: int | None = None) -> bool:
    """Test Telegram bot connection."""
    bot = Bot(token=bot_token)
    try:
        me = await bot.get_me()
        log.info(f"Bot connected: @{me.username} ({me.first_name})")
        await bot.send_message(
            chat_id=chat_id,
            message_thread_id=topic_id,
            text="✅ LinkedIn Job Bot — kết nối thành công!\n🤖 Sẵn sàng gửi thông báo việc làm.",
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

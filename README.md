# LinkedIn Frontend Jobs → Telegram Bot 🤖

Tự động scrape **Frontend Developer jobs** trên LinkedIn và gửi thông báo lên **Telegram** mỗi ngày lúc **13:20** (giờ Việt Nam).

## ✨ Tính năng

- 🔍 Scrape LinkedIn Jobs bằng Playwright (headless browser)
- 🎯 Filter: Junior Level | Onsite | 24h qua | HCMC
- 📤 Gửi thông báo Telegram với format đẹp
- 💾 Lưu lịch sử để không gửi job trùng lặp
- ⏰ Tự động chạy lúc 13:20 hàng ngày

## 🚀 Setup

### 1. Tạo virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Cài dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Cấu hình `.env`
```bash
cp .env.example .env
# Đã có sẵn bot token và chat ID
```

## 📦 Cấu trúc project

```
linkedinscraper/
├── src/
│   ├── scraper/linkedin_scraper.py   # Core scraping logic
│   ├── bot/telegram_bot.py           # Telegram notifications
│   ├── storage/job_store.py          # SQLite (tránh duplicate)
│   └── utils/logger.py               # Logging
├── config/config.yaml                # Cấu hình keywords, schedule
├── data/jobs.db                      # Auto-created SQLite DB
├── main.py                           # Chạy thủ công
├── scheduler.py                      # Chạy tự động theo lịch
└── .env                              # Bot token & Chat ID
```

## 🎮 Cách dùng

```bash
# Test kết nối Telegram
python main.py --test-telegram

# Scrape thử (không gửi Telegram)
python main.py --dry-run

# Chạy đầy đủ (scrape + gửi Telegram)
python main.py

# Chạy scheduler (tự động mỗi ngày 13:20)
python scheduler.py
```

## ⚙️ Tùy chỉnh config

Sửa file `config/config.yaml`:
- **keywords**: Thêm/bớt từ khóa tìm kiếm
- **location**: Địa điểm (mặc định HCMC)
- **experience_level**: `2` = Entry/Junior, `3` = Mid, `4` = Senior
- **scheduler.hour/minute**: Giờ chạy tự động

## 📱 Format message Telegram

```
━━━━━━━━━━━━━━━━━━━━
💼 Frontend Developer
🏢 Shopee Vietnam
📍 Ho Chi Minh City
⏰ 2 hours ago
🔗 Xem chi tiết
━━━━━━━━━━━━━━━━━━━━
```

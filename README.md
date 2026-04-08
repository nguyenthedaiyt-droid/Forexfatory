# ForexFactory News → Discord Bot 🤖

Bot tự động cào tin tức từ [ForexFactory](https://www.forexfactory.com/news) và gửi thông báo về **Discord** theo mức độ ảnh hưởng (**High / Medium / Low Impact**).

Vận hành hoàn toàn tự động bằng **GitHub Actions** (chạy mỗi 30 phút).

---

## ✨ Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| 🔴 High Impact | Bật/tắt gửi tin High Impact |
| 🟡 Medium Impact | Bật/tắt gửi tin Medium Impact |
| 🟢 Low Impact | Bật/tắt gửi tin Low Impact |
| 🚫 Anti-duplicate | Không gửi lại tin đã thông báo |
| ⏱️ Auto-schedule | Tự động chạy mỗi 30 phút |
| 🧪 Dry-run mode | Test mà không gửi Discord |

---

## 📋 Yêu cầu

- Python 3.12+
- GitHub repository (free tier đủ dùng)
- Discord Server + Webhook URL

---

## 🚀 Hướng dẫn Cài đặt

### Bước 1: Fork / Clone repo này lên GitHub

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### Bước 2: Tạo Discord Webhook

1. Vào Discord Server → **Server Settings** → **Integrations** → **Webhooks**
2. Nhấn **New Webhook** → đặt tên → chọn channel
3. Copy **Webhook URL**

### Bước 3: Thêm Secret vào GitHub

1. Vào repo GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Nhấn **New repository secret**
3. Điền:
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Value**: Paste Webhook URL vừa copy
4. Nhấn **Add secret**

### Bước 4: Cấu hình lọc Impact (tùy chọn)

Mở file `config.py` và điều chỉnh:

```python
FILTER_HIGH_IMPACT   = True   # 🔴 Bật/tắt tin High Impact
FILTER_MEDIUM_IMPACT = True   # 🟡 Bật/tắt tin Medium Impact
FILTER_LOW_IMPACT    = False  # 🟢 Bật/tắt tin Low Impact
```

### Bước 5: Push lên GitHub

```bash
git add .
git commit -m "Initial setup"
git push origin main
```

GitHub Actions sẽ **tự động kích hoạt** theo lịch cron mỗi 30 phút.

---

## 🧪 Chạy thử thủ công

### Trên GitHub Actions (Recommended)

1. Vào tab **Actions** trên GitHub
2. Chọn workflow **ForexFactory News → Discord Bot**
3. Nhấn **Run workflow**
4. Chọn `dry_run = true` để test không gửi Discord

### Trên máy local

```bash
# Cài dependencies
pip install -r requirements.txt
playwright install chromium

# Chạy thử (không gửi Discord)
python main.py --dry-run

# Chạy thật (cần set webhook URL)
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python main.py
```

---

## 📁 Cấu trúc dự án

```
├── .github/
│   └── workflows/
│       └── news_bot.yml      # GitHub Actions workflow
├── src/
│   ├── scraper.py            # Cào tin (Playwright + BeautifulSoup)
│   ├── filter.py             # Lọc theo Impact Level
│   ├── notifier.py           # Gửi Discord Webhook
│   └── storage.py            # Quản lý cache
├── main.py                   # Entry point
├── config.py                 # Cấu hình
├── requirements.txt          # Dependencies
└── sent_news.json            # Cache tin đã gửi (tự tạo)
```

---

## ⚙️ Cách hoạt động

```
GitHub Actions (mỗi 30 phút)
    │
    ▼
Playwright Chromium → ForexFactory /news (vượt anti-bot)
    │
    ▼
BeautifulSoup → Parse tin tức (title, impact, url, time)
    │
    ▼
Filter → Lọc theo High/Medium/Low + bỏ tin đã gửi
    │
    ▼
Discord Webhook → Gửi Embed màu sắc đẹp
    │
    ▼
Cache → Lưu sent_news.json (GitHub Actions Cache)
```

---

## 🎨 Ví dụ Discord Message

```
🔴 [HIGH IMPACT]
USD Non-Farm Payrolls
💱 USD  ⚡ HIGH IMPACT  🕐 2h ago
https://www.forexfactory.com/news/...
```

---

## ❓ Câu hỏi thường gặp

**Q: Bot có bị block không?**
> Playwright dùng Chrome thật nên khó bị detect. Nếu bị block, thử giảm tần suất chạy.

**Q: Có thể chạy mỗi 5 phút không?**
> Có thể đổi cron thành `*/5 * * * *` trong `news_bot.yml`, nhưng sẽ tiêu tốn nhiều GitHub Actions minutes.

**Q: Làm sao reset cache tin đã gửi?**
> Vào GitHub **Actions** → **Caches** → xóa cache `sent-news-cache-Linux`.

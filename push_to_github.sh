#!/bin/bash
# push_to_github.sh - Chạy file này trong Git Bash

cd /d/Indicaters/news

# Cài đặt remote (nếu chưa có)
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/nguyenthedai2k3-design/obito_forexfatory.git

# Kéo commit lịch sử từ remote (có README.md từ "Initial commit")
git fetch origin main

# Gộp vào local (cho phép lịch sử khác nhau)
git merge origin/main --allow-unrelated-histories -m "Merge: tích hợp tool ForexFactory news bot" || true

# Đảm bảo branch tên là main
git branch -M main

# Add toàn bộ code mới
git add .

# Commit
git commit -m "feat: ForexFactory News → Discord Bot via GitHub Actions

- src/scraper.py: Cào tin bằng Playwright + BeautifulSoup (vượt anti-bot)
- src/filter.py: Lọc High/Medium/Low Impact
- src/notifier.py: Gửi Discord Embed webhook (màu theo impact)
- src/storage.py: Cache sent_news.json tránh gửi trùng
- main.py: Entry point với --dry-run support
- config.py: Cấu hình lọc Impact level
- .github/workflows/news_bot.yml: GitHub Actions cron 30 phút"

# Push lên GitHub
git push -u origin main

echo "✅ Đã push thành công lên https://github.com/nguyenthedai2k3-design/obito_forexfatory"

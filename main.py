"""
main.py - Entry point của ForexFactory News Discord Bot
"""

import asyncio
import argparse
import sys

from src.scraper  import scrape_news
from src.filter   import filter_news
from src.analyzer import setup_analyzer, analyze_news_impact
from src.notifier import send_news_to_discord
from src.storage  import load_sent_ids, save_sent_ids


# ============================================================
# ARGUMENT PARSER
# ============================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ForexFactory News → Discord Bot",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chạy thử: parse và log ra console, KHÔNG gửi Discord",
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=None,
        help="Discord Webhook URL (ghi đè biến môi trường DISCORD_WEBHOOK_URL)",
    )
    return parser.parse_args()


# ============================================================
# MAIN FLOW
# ============================================================

async def main() -> None:
    args = _parse_args()
    dry_run = args.dry_run

    print("=" * 60)
    print("🚀 ForexFactory News Discord Bot - Bắt đầu")
    if dry_run:
        print("⚙️  Chế độ: DRY-RUN (chỉ log, không gửi Discord)")
    print("=" * 60)

    # 1. Cào tin từ ForexFactory
    print("\n[1/4] 🌐 Đang cào tin tức từ ForexFactory...")
    all_news = await scrape_news()

    if not all_news:
        print("❌ Không lấy được tin tức. Kết thúc.")
        sys.exit(0)

    # 2. Đọc danh sách tin đã gửi
    print("\n[2/4] 📂 Đọc danh sách tin đã gửi...")
    sent_ids = load_sent_ids()
    print(f"     → Đã có {len(sent_ids)} tin trong cache")

    # 3. Lọc tin mới theo impact + deduplicate
    print("\n[3/4] 🔍 Lọc tin tức theo Impact Level...")
    new_news = filter_news(all_news, sent_ids)

    if not new_news:
        print("ℹ️  Không có tin mới cần gửi. Kết thúc.")
        sys.exit(0)

    # Sắp xếp tin tức ưu tiên mới nhất đẩy lên đầu
    new_news.sort(key=lambda x: x.unix_time, reverse=True)

    # 4. Phân tích tác động với Gemini AI
    print("\n[4/5] 🤖 Đang dùng Gemini để nhận định thị trường...")
    setup_analyzer()
    for item in new_news:
        print(f"     → Phân tích: {item.title[:50]}...")
        result = await analyze_news_impact(item.title, item.summary)
        if isinstance(result, dict):
            item.title = result.get("title", item.title)
            item.summary = result.get("summary", item.summary)
            item.ai_analysis = result.get("analysis", "")

    # 5. Gửi lên Discord
    print(f"\n[5/5] 📨 Gửi {len(new_news)} tin lên Discord...")
    sent_ids_new = send_news_to_discord(
        news_items=new_news,
        webhook_url=args.webhook_url,
        dry_run=dry_run,
    )

    # 6. Cập nhật cache nếu không phải dry-run
    if not dry_run and sent_ids_new:
        print("\n[6/6] 💾 Cập nhật cache...")
        save_sent_ids(sent_ids, sent_ids_new)

    print("\n" + "=" * 60)
    print(f"✅ Hoàn thành! Đã gửi {len(sent_ids_new)} tin mới.")
    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())

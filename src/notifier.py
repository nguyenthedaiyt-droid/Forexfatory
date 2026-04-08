"""
notifier.py - Gửi tin tức lên Discord thông qua Webhook
"""

import os
import time
import requests

from config import (
    BOT_USERNAME,
    BOT_AVATAR_URL,
    COLOR_HIGH_IMPACT,
    COLOR_MEDIUM_IMPACT,
    COLOR_LOW_IMPACT,
    EMOJI_HIGH_IMPACT,
    EMOJI_MEDIUM_IMPACT,
    EMOJI_LOW_IMPACT,
    DISCORD_SEND_DELAY,
)
from src.scraper import NewsItem


# ============================================================
# HELPER - Lấy màu + emoji theo impact
# ============================================================

def _get_impact_style(impact: str) -> tuple[int, str, str]:
    """Trả về (color_int, emoji, label) theo impact level."""
    styles = {
        "high":    (COLOR_HIGH_IMPACT,   EMOJI_HIGH_IMPACT,   "HIGH IMPACT"),
        "medium":  (COLOR_MEDIUM_IMPACT, EMOJI_MEDIUM_IMPACT, "MEDIUM IMPACT"),
        "low":     (COLOR_LOW_IMPACT,    EMOJI_LOW_IMPACT,    "LOW IMPACT"),
        "unknown": (0x888888,            "⚪",                "UNKNOWN"),
    }
    return styles.get(impact.lower(), styles["unknown"])


# ============================================================
# HELPER - Tạo Discord Embed từ NewsItem
# ============================================================

def _build_embed(item: NewsItem) -> dict:
    """Tạo payload Discord Embed cho một tin tức."""
    color, emoji, label = _get_impact_style(item.impact)

    fields = []

    if item.currency:
        fields.append({
            "name": "💱 Currency",
            "value": f"`{item.currency}`",
            "inline": True,
        })

    if item.ai_analysis:
        fields.append({
            "name": "Market analysis AI",
            "value": item.ai_analysis,
            "inline": False,
        })

    fields.append({
        "name": "⚡ Impact",
        "value": f"{emoji} **{label}**",
        "inline": True,
    })

    if item.published_at:
        fields.append({
            "name": "🕐 Published",
            "value": item.published_at,
            "inline": True,
        })


    description = item.summary if item.summary else ""

    embed = {
        "title": item.title,
        "color": color,
        "description": description,
        "fields": fields,
        "footer": {
            "text": "𝙿𝚘𝚠𝚎𝚛𝚎𝚍 𝚋𝚢 𝙾𝚋𝚒𝚝𝚘 𝙽𝚎𝚠𝚜",
        },
    }

    return embed


# ============================================================
# MAIN NOTIFIER
# ============================================================

def send_news_to_discord(
    news_items: list[NewsItem],
    webhook_url: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    """
    Gửi từng NewsItem lên Discord dưới dạng Embed đẹp.
    Trả về danh sách news_id đã gửi thành công.

    Args:
        news_items:  Danh sách tin cần gửi
        webhook_url: Discord Webhook URL (ưu tiên biến môi trường DISCORD_WEBHOOK_URL)
        dry_run:     Nếu True, chỉ in ra console mà không gửi thật
    """
    if not webhook_url:
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")

    if not webhook_url and not dry_run:
        print("[NOTIFIER] ❌ Không tìm thấy DISCORD_WEBHOOK_URL!")
        return []

    succeeded: list[str] = []

    for item in news_items:
        embed = _build_embed(item)
        payload = {
            "embeds": [embed],
        }

        if dry_run:
            _, emoji, label = _get_impact_style(item.impact)
            print(f"[DRY-RUN] {emoji} [{label}] {item.title}")
            print(f"          🕐 {item.published_at}")
            if item.ai_analysis:
                print(f"          🤖 AI: {item.ai_analysis[:50]}...")
            print()
            succeeded.append(item.news_id)
            continue

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=15,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code in (200, 204):
                print(f"[NOTIFIER] ✅ Gửi thành công: {item.title[:60]}...")
                succeeded.append(item.news_id)
            elif response.status_code == 429:
                # Rate limit - chờ thêm
                retry_after = response.json().get("retry_after", 5)
                print(f"[NOTIFIER] ⏳ Rate limit! Chờ {retry_after}s...")
                time.sleep(retry_after + 1)
                # Thử lại 1 lần
                response2 = requests.post(webhook_url, json=payload, timeout=15)
                if response2.status_code in (200, 204):
                    succeeded.append(item.news_id)
            else:
                print(f"[NOTIFIER] ⚠️  Lỗi {response.status_code}: {response.text[:100]}")
        except requests.RequestException as e:
            print(f"[NOTIFIER] ❌ Lỗi kết nối: {e}")

        time.sleep(DISCORD_SEND_DELAY)

    print(f"[NOTIFIER] 📨 Đã gửi {len(succeeded)}/{len(news_items)} tin")
    return succeeded

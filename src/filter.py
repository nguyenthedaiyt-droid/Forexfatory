"""
filter.py - Lọc tin tức theo mức độ impact và loại bỏ tin đã gửi
"""

from config import (
    FILTER_HIGH_IMPACT,
    FILTER_MEDIUM_IMPACT,
    FILTER_LOW_IMPACT,
)
from src.scraper import NewsItem


# ============================================================
# LOGIC LỌC IMPACT
# ============================================================

def _is_impact_allowed(impact: str) -> bool:
    """Kiểm tra xem impact level có được bật trong config không."""
    impact_lower = impact.lower()
    if impact_lower == "high":
        return FILTER_HIGH_IMPACT
    if impact_lower == "medium":
        return FILTER_MEDIUM_IMPACT
    if impact_lower == "low":
        return FILTER_LOW_IMPACT
    # "unknown" impact: luôn bỏ qua để tránh spam
    return False


# ============================================================
# MAIN FILTER
# ============================================================

def filter_news(
    news_items: list[NewsItem],
    sent_ids: set[str],
) -> list[NewsItem]:
    """
    Lọc danh sách tin tức:
    1. Bỏ tin đã gửi (sent_ids)
    2. Bỏ tin không thỏa mãn Impact Level config
    Trả về danh sách tin mới cần gửi.
    """
    filtered: list[NewsItem] = []

    for item in news_items:
        if item.news_id in sent_ids:
            continue
        if not _is_impact_allowed(item.impact):
            continue
        filtered.append(item)

    impact_summary = {
        "high":    sum(1 for i in filtered if i.impact == "high"),
        "medium":  sum(1 for i in filtered if i.impact == "medium"),
        "low":     sum(1 for i in filtered if i.impact == "low"),
        "unknown": sum(1 for i in filtered if i.impact == "unknown"),
    }

    print(
        f"[FILTER] ✅ {len(filtered)} tin mới cần gửi "
        f"(🔴 High={impact_summary['high']} "
        f"🟡 Medium={impact_summary['medium']} "
        f"🟢 Low={impact_summary['low']})"
    )

    return filtered

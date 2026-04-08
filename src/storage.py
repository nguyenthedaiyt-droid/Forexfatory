"""
storage.py - Quản lý danh sách news_id đã gửi (tránh gửi trùng lặp)
"""

import json
import os
from pathlib import Path

from config import SENT_NEWS_FILE, MAX_SENT_IDS


# ============================================================
# ĐỌC DANH SÁCH TIN ĐÃ GỬI
# ============================================================

def load_sent_ids() -> set[str]:
    """Đọc file sent_news.json, trả về set các news_id đã gửi."""
    path = Path(SENT_NEWS_FILE)
    if not path.exists():
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("sent_ids", []))
    except (json.JSONDecodeError, KeyError):
        print(f"[STORAGE] ⚠️  File {SENT_NEWS_FILE} bị lỗi, reset về rỗng")
        return set()


# ============================================================
# LƯU DANH SÁCH TIN ĐÃ GỬI
# ============================================================

def save_sent_ids(sent_ids: set[str], new_ids: list[str]) -> None:
    """
    Thêm new_ids vào tập sent_ids và ghi ra file.
    Giới hạn tối đa MAX_SENT_IDS phần tử (FIFO, xóa cũ nhất).
    """
    # Gộp + giới hạn kích thước (giữ MAX_SENT_IDS phần tử mới nhất)
    combined = list(sent_ids) + new_ids
    if len(combined) > MAX_SENT_IDS:
        combined = combined[-MAX_SENT_IDS:]

    path = Path(SENT_NEWS_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sent_ids": combined}, f, ensure_ascii=False, indent=2)

    print(f"[STORAGE] 💾 Đã lưu {len(combined)} sent_ids vào {SENT_NEWS_FILE}")

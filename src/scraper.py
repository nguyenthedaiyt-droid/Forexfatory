"""
scraper.py - Cào tin tức từ ForexFactory bằng Playwright (vượt anti-bot)
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession

from config import FOREXFACTORY_NEWS_URL


# ============================================================
# DATA MODEL
# ============================================================

@dataclass
class NewsItem:
    news_id: str          # Hash duy nhất từ URL
    title: str
    url: str
    impact: str           # "high" | "medium" | "low" | "unknown"
    published_at: str     # Chuỗi thời gian gốc từ trang
    summary: str = ""
    currency: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================
# HELPER - Tạo ID duy nhất từ URL
# ============================================================

def _make_news_id(url: str) -> str:
    return hashlib.md5(url.strip().encode()).hexdigest()


# ============================================================
# HELPER - Phân tích mức độ impact từ HTML
# ============================================================

def _parse_impact(element) -> str:
    """
    ForexFactory đánh dấu impact qua class của thẻ img trong news-block__details.
    Class pattern: svg-img--impact-ff-high / medium / low
    """
    # Tìm img có class chứa impact-ff-
    img = element.find("img", class_=re.compile(r"impact-ff-", re.I))
    if img:
        classes = " ".join(img.get("class", []))
        if "impact-ff-high"   in classes: return "high"
        if "impact-ff-medium" in classes: return "medium"
        if "impact-ff-low"    in classes: return "low"
    return "unknown"


# ============================================================
# HELPER - Parse từng phần tử tin tức
# ============================================================

def _parse_news_element(el) -> Optional[NewsItem]:
    """Parse một phần tử `div.news-block__item` thành NewsItem."""
    try:
        # Tiêu đề + URL: nằm trong div.news-block__title -> a
        title_container = el.find("div", class_="news-block__title")
        if not title_container:
            return None

        title_tag = title_container.find("a")
        if not title_tag:
            return None

        # Lấy title
        title = title_tag.get_text(strip=True)
        if not title:
            title = title_tag.get("title", "").strip()
        if not title:
            return None

        href = title_tag.get("href", "")
        if href.startswith("/"):
            href = "https://www.forexfactory.com" + href
        if not href or "/news/" not in href:
            return None

        # Impact: img[class*=impact-ff-] trong news-block__details
        impact = _parse_impact(el)

        # Thời gian: span.nowrap có title attribute chứa ngày giờ đầy đủ
        time_tag = el.find("span", class_="nowrap")
        published_at = time_tag.get("title", "") or time_tag.get_text(strip=True) if time_tag else ""

        # Preview / Summary
        preview_tag = el.find("div", class_="news-block__preview")
        summary = preview_tag.get_text(strip=True) if preview_tag else ""

        news_id = _make_news_id(href)

        return NewsItem(
            news_id=news_id,
            title=title,
            url=href,
            impact=impact,
            published_at=published_at,
            summary=summary,
        )
    except Exception:
        return None


# ============================================================
# HELPER - Parse HTML toàn trang
# ============================================================

def _parse_page_html(html: str) -> list[NewsItem]:
    """
    Phân tích HTML toàn trang ForexFactory.
    Container thực tế: div.news-block__item (chứa cả headline và story)
    Chỉ lấy loại headline/story, bỏ qua comment.
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[NewsItem] = []
    seen_ids: set[str] = set()

    # Lấy tất cả div có class news-block__item
    elements = soup.find_all("div", class_=re.compile(r"^news-block__item", re.I))

    for el in elements:
        # Bỏ qua item loại comment (không phải tin tức)
        classes = " ".join(el.get("class", []))
        if "comment" in classes:
            continue

        item = _parse_news_element(el)
        if item and item.title and item.url and item.news_id not in seen_ids:
            seen_ids.add(item.news_id)
            results.append(item)

    print(f"[SCRAPER] 📊 Tìm thấy {len(elements)} elements, parse được {len(results)} tin")
    return results


# ============================================================
# MAIN SCRAPER - Chạy Playwright headless
# ============================================================

async def scrape_news() -> list[NewsItem]:
    """
    Sử dụng curl_cffi giả lập Chrome để fetch HTML.
    Vượt qua Cloudflare dễ dàng mà không cần headless browser nặng nề.
    """
    news_items: list[NewsItem] = []

    try:
        print(f"[SCRAPER] 🌐 Truy cập: {FOREXFACTORY_NEWS_URL}")
        async with AsyncSession(impersonate="chrome") as session:
            # Gửi request với định danh trình duyệt thật
            response = await session.get(FOREXFACTORY_NEWS_URL, timeout=30)

            html = response.text
            print(f"[SCRAPER DEBUG] Status: {response.status_code}")
            print(f"[SCRAPER DEBUG] HTML length: {len(html)} chars")

            if "news-block__item" not in html:
                print("[SCRAPER ⚠️] Không tìm thấy 'news-block__item' trong HTML, có thể bị chặn bảo mật.")

            # Trích xuất dữ liệu
            news_items = _parse_page_html(html)

    except Exception as e:
        print(f"[SCRAPER] ❌ Lỗi: {e}")

    print(f"[SCRAPER] ✅ Cào được {len(news_items)} tin tức")
    return news_items

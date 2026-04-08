"""
scraper.py - Cào tin tức từ ForexFactory bằng Playwright (vượt anti-bot)
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

from config import (
    FOREXFACTORY_NEWS_URL,
    PLAYWRIGHT_TIMEOUT,
)


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
    ForexFactory dùng class CSS để đánh dấu impact.
    Thử nhiều selector khả dĩ theo cấu trúc HTML thực tế.
    """
    impact_map = {
        "high":   ["impact-h", "high",   "impact--high",   "ico-impact-yel"],
        "medium": ["impact-m", "medium", "impact--medium", "ico-impact-ora"],
        "low":    ["impact-l", "low",    "impact--low",    "ico-impact-yel-low"],
    }

    # Tìm tất cả class trong element con có chứa từ "impact"
    target = element.find(class_=re.compile(r"impact", re.I))
    if not target:
        return "unknown"

    classes = " ".join(target.get("class", []))
    classes_lower = classes.lower()

    for level, keywords in impact_map.items():
        if any(kw in classes_lower for kw in keywords):
            return level

    # Fallback: đọc alt text của img icon
    img = element.find("img", alt=re.compile(r"high|medium|low", re.I))
    if img:
        alt = img.get("alt", "").lower()
        if "high"   in alt: return "high"
        if "medium" in alt: return "medium"
        if "low"    in alt: return "low"

    return "unknown"


# ============================================================
# HELPER - Parse từng phần tử tin tức
# ============================================================

def _parse_news_element(el) -> Optional[NewsItem]:
    """Parse một phần tử `.news-item` thành NewsItem."""
    try:
        # Tiêu đề + URL
        title_tag = el.find("a", class_=re.compile(r"title|headline|news__title", re.I))
        if not title_tag:
            title_tag = el.find("a", href=re.compile(r"/news/"))
        if not title_tag:
            return None

        title = title_tag.get_text(strip=True)
        href  = title_tag.get("href", "")
        if href.startswith("/"):
            href = "https://www.forexfactory.com" + href
        if not href:
            return None

        # Impact
        impact = _parse_impact(el)

        # Thời gian đăng
        time_tag = el.find(["time", "span"], class_=re.compile(r"time|date|ago|published", re.I))
        published_at = time_tag.get_text(strip=True) if time_tag else ""

        # Summary (đoạn mô tả ngắn)
        summary_tag = el.find(class_=re.compile(r"summary|excerpt|detail|descript", re.I))
        summary = summary_tag.get_text(strip=True) if summary_tag else ""

        # Currency tag
        currency_tag = el.find(class_=re.compile(r"currency|flag|symbol", re.I))
        currency = currency_tag.get_text(strip=True) if currency_tag else ""

        news_id = _make_news_id(href)

        return NewsItem(
            news_id=news_id,
            title=title,
            url=href,
            impact=impact,
            published_at=published_at,
            summary=summary,
            currency=currency,
        )
    except Exception:
        return None


# ============================================================
# HELPER - Parse HTML toàn trang
# ============================================================

def _parse_page_html(html: str) -> list[NewsItem]:
    """
    Phân tích HTML toàn trang, tìm các container tin tức.
    Thử nhiều selector để linh hoạt với thay đổi cấu trúc trang.
    """
    soup = BeautifulSoup(html, "lxml")
    results: list[NewsItem] = []

    # Thử các container selector phổ biến của ForexFactory
    container_selectors = [
        {"class": re.compile(r"^news-item", re.I)},
        {"class": re.compile(r"^flexposts__story", re.I)},
        {"class": re.compile(r"news__story", re.I)},
        {"class": re.compile(r"story-item", re.I)},
    ]

    elements = []
    for selector in container_selectors:
        found = soup.find_all(True, selector)
        if found:
            elements = found
            break

    # Fallback: tìm mọi thẻ article
    if not elements:
        elements = soup.find_all("article")

    for el in elements:
        item = _parse_news_element(el)
        if item and item.title and item.url:
            results.append(item)

    return results


# ============================================================
# MAIN SCRAPER - Chạy Playwright headless
# ============================================================

async def scrape_news() -> list[NewsItem]:
    """
    Launch Playwright Chromium, navigate đến ForexFactory /news,
    chờ content load xong, parse HTML và trả về danh sách NewsItem.
    """
    news_items: list[NewsItem] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-dev-shm-usage",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
            locale="en-US",
        )

        page: Page = await context.new_page()

        # Ẩn dấu hiệu automation
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        try:
            await page.goto(FOREXFACTORY_NEWS_URL, timeout=PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")

            # Chờ content tin tức xuất hiện (thử nhiều selector)
            content_selectors = [
                ".news-item",
                ".flexposts__story",
                ".news__story",
                "article",
            ]
            for sel in content_selectors:
                try:
                    await page.wait_for_selector(sel, timeout=15_000)
                    break
                except PlaywrightTimeoutError:
                    continue

            # Lấy toàn bộ HTML sau khi JS render xong
            html = await page.content()
            news_items = _parse_page_html(html)

        except PlaywrightTimeoutError:
            print("[SCRAPER] ⚠️  Timeout khi tải trang ForexFactory")
        except Exception as e:
            print(f"[SCRAPER] ❌ Lỗi: {e}")
        finally:
            await browser.close()

    print(f"[SCRAPER] ✅ Cào được {len(news_items)} tin tức")
    return news_items

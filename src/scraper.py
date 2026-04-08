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
        # Tiêu đề + URL: dùng class news-block__image-link
        title_tag = el.find("a", class_="news-block__image-link")
        if not title_tag:
            return None

        # Lấy title từ attribute "title" (đầy đủ hơn text content)
        title = title_tag.get("title", "").strip()
        if not title:
            title = title_tag.get_text(strip=True)
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
            print(f"[SCRAPER] 🌐 Truy cập: {FOREXFACTORY_NEWS_URL}")
            await page.goto(FOREXFACTORY_NEWS_URL, timeout=PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")

            # In URL hiện tại để phát hiện redirect (Cloudflare challenge...)
            current_url = page.url
            print(f"[SCRAPER DEBUG] URL sau khi load: {current_url}")
            print(f"[SCRAPER DEBUG] Title: {await page.title()}")

            # Chờ cứng 5 giây để JS render
            await page.wait_for_timeout(5000)

            # Chụp screenshot để debug (lưu vào thư mục hiện tại)
            await page.screenshot(path="debug_screenshot.png", full_page=False)
            print("[SCRAPER DEBUG] Đã chụp screenshot: debug_screenshot.png")

            # Chờ container tin tức thực tế của ForexFactory
            try:
                await page.wait_for_selector(".news-block__item", timeout=15_000)
                print("[SCRAPER] ✅ Selector matched: .news-block__item")
            except PlaywrightTimeoutError:
                print("[SCRAPER] ⚠️  .news-block__item không tìm thấy, tiếp tục parse...")

            # Lấy toàn bộ HTML sau khi JS render xong
            html = await page.content()
            print(f"[SCRAPER DEBUG] HTML length: {len(html)} chars")
            print(f"[SCRAPER DEBUG] HTML snippet:\n{html[:800]}")

            # Dump full HTML để phân tích selector
            with open("debug_full.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("[SCRAPER DEBUG] Đã lưu HTML đầy đủ: debug_full.html")

            news_items = _parse_page_html(html)

        except PlaywrightTimeoutError:
            print("[SCRAPER] ⚠️  Timeout khi tải trang ForexFactory")
            try:
                await page.screenshot(path="debug_timeout.png")
                print("[SCRAPER DEBUG] Đã chụp screenshot lỗi: debug_timeout.png")
            except Exception:
                pass
        except Exception as e:
            print(f"[SCRAPER] ❌ Lỗi: {e}")
        finally:
            await browser.close()

    print(f"[SCRAPER] ✅ Cào được {len(news_items)} tin tức")
    return news_items

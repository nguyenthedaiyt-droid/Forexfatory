# ============================================================
# CONFIG - Cấu hình ForexFactory News Discord Bot
# ============================================================

# --- Lọc Impact Level (True = bật, False = tắt) ---
FILTER_HIGH_IMPACT   = True
FILTER_MEDIUM_IMPACT = True
FILTER_LOW_IMPACT    = False

# --- Giới hạn bộ nhớ (tránh file JSON phình to) ---
MAX_SENT_IDS = 500

# --- File lưu danh sách tin đã gửi ---
SENT_NEWS_FILE = "sent_news.json"

# --- Tên hiển thị trong Discord ---
BOT_USERNAME   = "Obito News Bot"
BOT_AVATAR_URL = "https://www.forexfactory.com/favicon.ico"

# --- Màu Discord Embed theo impact ---
COLOR_HIGH_IMPACT   = 0xFF4444   # Đỏ
COLOR_MEDIUM_IMPACT = 0xFFA500   # Cam
COLOR_LOW_IMPACT    = 0x00AA44   # Xanh lá

# --- Emoji theo impact ---
EMOJI_HIGH_IMPACT   = "🔴"
EMOJI_MEDIUM_IMPACT = "🟡"
EMOJI_LOW_IMPACT    = "🟢"

# --- URL ForexFactory ---
FOREXFACTORY_NEWS_URL = "https://www.forexfactory.com/news"

# --- Playwright timeout (ms) ---
PLAYWRIGHT_TIMEOUT = 60_000  # 60 giây

# --- Delay giữa các lần gửi Discord (tránh rate limit) ---
DISCORD_SEND_DELAY = 1.0  # giây

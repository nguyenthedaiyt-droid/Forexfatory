import os
from dotenv import load_dotenv
from discord_notifier import DiscordNotifier

# Load env
load_dotenv()

def test_connection():
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    print(f"Webhook URL hiện tại: {webhook_url}")
    
    if not webhook_url:
        print("LỖI: Chưa cấu hình DISCORD_WEBHOOK_URL trong file .env")
        return

    notifier = DiscordNotifier(webhook_url)
    
    print("Đang gửi tin nhắn test...")
    notifier.send_message("👋 Xin chào! Đây là tin nhắn kiểm tra từ Scraper Project.")
    
    print("Đang gửi embed test...")
    notifier.send_embed(
        title="Test Embed Notification",
        description="Nếu bạn nhìn thấy tin nhắn này, hệ thống thông báo đã hoạt động ổn định! 🚀",
        color=0x00ff00
    )

if __name__ == "__main__":
    test_connection()

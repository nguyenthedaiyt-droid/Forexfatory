import os
from dotenv import load_dotenv
from discord_notifier import DiscordNotifier
import watcher

# Load env variables
load_dotenv()

def test_watcher_notification():
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("LỖI: Chưa cấu hình DISCORD_WEBHOOK_URL trong file .env")
        return

    notifier = DiscordNotifier(webhook_url)
    
    # Mock Event Data (Dictionary imitating a DataFrame row)
    mock_event = {
        "Time": "07:30",
        "Impact": "High",
        "Event": "Test: Core Durable Goods Orders m/m",
        "Previous": "5.4%",
        "Forecast": "-1.8%",
        "Actual": "-1.4%",
        "ActualColor": "green" # Mocking a "Better" result
    }
    
    print("Đang tạo tin nhắn mẫu (Code Block Grid)...")
    title, description, color, fields = watcher.prepare_event_embed(mock_event)
    
    # Debug print
    print(f"Title: {title}")
    print(f"Color: {color}")
    print("Description:")
    print(description)
    print("Fields:")
    print(fields)
    
    print("\nĐang gửi lên Discord...")
    notifier.send_embed(title, description, color, fields=fields)
    print("✅ Đã gửi xong! Kiểm tra Discord của bạn.")

if __name__ == "__main__":
    test_watcher_notification()

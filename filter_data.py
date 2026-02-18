import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from discord_notifier import DiscordNotifier

# Load biến môi trường
load_dotenv()

def filter_data(currency="USD"):
    try:
        # Đọc dữ liệu
        df = pd.read_csv("economic_calendar.csv")
        
        # Lấy ngày hiện tại theo định dạng trong CSV (VD: Thu Feb 12 2026)
        # Lưu ý: Hệ thống đang giả lập năm 2026, nhưng datetime.now() sẽ lấy giờ hệ thống thực.
        # Tuy nhiên, trong context này, user/metadata báo là 2026-02-12.
        # Python datetime.now() sẽ lấy theo giờ máy (metadata).
        
        today = datetime.now()
        # Định dạng ngày cho giống CSV: %a %b %d %Y (VD: Thu Feb 12 2026)
        # Cần chú ý locale, nếu máy user dùng tiếng Việt/Khác thì %a %b sẽ khác.
        # Nhưng dữ liệu trong CSV là tiếng Anh ("Thu", "Feb").
        # Ở đây ta giả sử datetime basic tiếng Anh.
        
        # Calculate NY Time (UTC-5)
        # Note: Scraper đã convert sang NY Time rồi.
        # Ta chỉ cần tính "Hôm nay là ngày nào ở NY?" để filter.
        
        # ---------------------------------------------------------
        # Logic Lọc (Simplified)
        # CSV đã chứa dữ liệu của "Today (UTC)" và Timezone UTC.
        # Scraper đã xử lý việc lọc ngày.
        # Ở đây ta chỉ cần lấy tất cả (hoặc lọc thêm Impact/Currency nếu muốn chắc chắn).
        # ---------------------------------------------------------
        
        filtered_rows = []
        
        for index, row in df.iterrows():
            # 1. Check Currency (Double check)
            if row['Currency'] != currency: continue
            
            # 2. Check Impact
            if row['Impact'] == 'Low': continue
            
            # 3. Date Filter: Scraper has handled this.
            # Just take the row.

            # Match!
            item = row.to_dict()
            filtered_rows.append(item)

        # Convert list back to DataFrame
        filtered_df = pd.DataFrame(filtered_rows)
        
        if filtered_df.empty:
            print("Không tìm thấy dữ liệu phù hợp.")
            # Debug: In thử các ngày có trong file
            print("Các ngày có trong dữ liệu:", df['Date'].unique())
        else:
            print(f"Tìm thấy {len(filtered_df)} sự kiện:")
            print(filtered_df[['Time', 'Impact', 'Event', 'Actual', 'Forecast', 'Previous']].to_string(index=False))
            
            # Format tin nhắn để gửi Discord
            try:
                webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
                if webhook_url:
                    notifier = DiscordNotifier(webhook_url)
                    
                    # Tạo nội dung tin nhắn dạng Compact + Clean
                    # Format: `TIME` ICON `CUR` | **Event Name**
                    # Ví dụ: `12:45am` 🟡 `USD` | **FOMC Member Barr Speaks**
                    
                    details = ""
                    highest_impact_color = 0x00ff00 

                    for index, row in filtered_df.iterrows():
                        # Xử lý Impact
                        impact_icon = "⚪"
                        if row['Impact'] == 'High': 
                            impact_icon = "🔴"
                            highest_impact_color = 0xff0000 
                        elif row['Impact'] == 'Medium': 
                            impact_icon = "🟠"
                            if highest_impact_color != 0xff0000: highest_impact_color = 0xffa500
                        elif row['Impact'] == 'Low':
                            impact_icon = "🟡"
                        
                        event_name = str(row['Event'])
                        
                        # Time đã được convert ở trên rồi
                        time_str = str(row['Time'])

                        # Format dòng gọn gàng
                        # Ví dụ: `08:30` 🟡 | **FOMC Member Barr Speaks**
                        line = f"`{time_str}` {impact_icon} | **{event_name}**\n"
                        details += line

                    # Ghép lại thành nội dung hoàn chỉnh
                    description = f"{details}"
                    
                    # Gửi Embed
                    title = f"📅 Tin tức {currency} - {row['Date']} (UTC)"
                    notifier.send_embed(title, description, color=highest_impact_color)
                else:
                    print("Không tìm thấy DISCORD_WEBHOOK_URL trong file .env")
            except Exception as e:
                print(f"Lỗi khi gửi Discord: {e}")

            # Lưu ra file riêng nếu muốn
            filtered_df.to_csv(f"{currency}_today.csv", index=False)
            
    except FileNotFoundError:
        print("Chưa có file data. Hãy chạy scraper.py trước.")
    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    filter_data("USD")

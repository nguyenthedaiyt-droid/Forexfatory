import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Cấu hình Selenium
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Chạy ngầm
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Fake user agent để tránh bị chặn
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Lỗi khởi tạo driver: {e}")
        return None
        
    return driver

def get_economic_calendar():
    driver = setup_driver()
    if not driver:
        return
    # Xây dựng URL: Scrape Today và Tomorrow (UTC context) để cover lệch múi giờ
    # Vì Local Time (VN GMT+7) đi trước UTC, nên các tin cuối ngày UTC (17:00+) sẽ rơi vào ngày hôm sau ở VN.
    
    utc_now = datetime.utcnow()
    target_date_utc = utc_now.date() 
    print(f"Ngày mục tiêu (UTC): {target_date_utc}")
    
    # List ngày cần cào: Hôm nay và Ngày mai
    days_to_scrape = [utc_now, utc_now + timedelta(days=1)]
    
    all_events = []
    
    for scrape_date in days_to_scrape:
        day_str = scrape_date.strftime("%b%d.%Y").lower() # e.g. feb18.2026
        url = f"https://www.forexfactory.com/calendar?day={day_str}"
        print(f"Đang truy cập: {url}")
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "calendar__table"))
            )
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find("table", class_="calendar__table")
            
            current_date_text = ""
            current_time_text = ""
            
            rows = table.find_all("tr", class_="calendar__row")
            print(f" -> Tìm thấy {len(rows)} dòng dữ liệu.")
            
            current_year = "2026"
            
            for row in rows:
                # 1. Lấy ngày
                date_cell = row.find("td", class_="calendar__date")
                if date_cell:
                    d_text = date_cell.get_text(" ", strip=True) 
                    if d_text:
                        current_date_text = d_text
                        
                # 2. Lấy tiền tệ
                currency_cell = row.find("td", class_="calendar__currency")
                currency = currency_cell.text.strip() if currency_cell else ""
                
                # Filter USD
                if currency != "USD":
                    continue
                    
                # 3. Lấy giờ
                time_cell = row.find("td", class_="calendar__time")
                t_text = time_cell.text.strip() if time_cell else ""
                
                if t_text == "":
                    t_text = current_time_text
                else:
                    current_time_text = t_text
                
                # 4. Convert & Filter UTC Today
                final_date_str = ""
                final_time_str = ""
                is_target_day_utc = False
                
                if "am" in t_text or "pm" in t_text:
                    try:
                        raw_dt_str = f"{current_date_text} {current_year} {t_text}"
                        dt_vn = datetime.strptime(raw_dt_str, "%a %b %d %Y %I:%M%p")
                        
                        # VN -> UTC (-7)
                        dt_utc = dt_vn - timedelta(hours=7)
                        
                        if dt_utc.date() == target_date_utc:
                            is_target_day_utc = True
                            final_date_str = dt_utc.strftime(f"%a %b %d %Y")
                            final_time_str = dt_utc.strftime("%H:%M")
                    except:
                        pass
                elif "All Day" in t_text:
                    # All Day logic (Simplified)
                     try:
                        header_dt = datetime.strptime(f"{current_date_text} {current_year}", "%a %b %d %Y")
                        if header_dt.date() == target_date_utc:
                            is_target_day_utc = True
                            final_date_str = header_dt.strftime(f"%a %b %d %Y")
                            final_time_str = "All Day"
                     except:
                        pass
                
                if not is_target_day_utc:
                    continue

                # 5. Get details
                impact_cell = row.find("td", class_="calendar__impact")
                impact = "Non-Economic"
                if impact_cell:
                    span = impact_cell.find("span")
                    if span:
                        span_class = span.get("class", [])
                        if "icon--ff-impact-red" in span_class: impact = "High"
                        elif "icon--ff-impact-ora" in span_class: impact = "Medium"
                        elif "icon--ff-impact-yel" in span_class: impact = "Low"
                
                event_cell = row.find("td", class_="calendar__event")
                event_name = event_cell.text.strip() if event_cell else ""
                
                if not event_name: continue

                actual = row.find("td", class_="calendar__actual").text.strip() if row.find("td", class_="calendar__actual") else ""
                forecast = row.find("td", class_="calendar__forecast").text.strip() if row.find("td", class_="calendar__forecast") else ""
                previous = row.find("td", class_="calendar__previous").text.strip() if row.find("td", class_="calendar__previous") else ""
                
                all_events.append({
                    "Date": final_date_str, 
                    "Time": final_time_str,
                    "Currency": currency,
                    "Impact": impact,
                    "Event": event_name,
                    "Actual": actual,
                    "Forecast": forecast,
                    "Previous": previous
                })
                
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # Save
    df = pd.DataFrame(all_events)
    # Remove duplicates just in case
    if not df.empty:
        df.drop_duplicates(inplace=True)
        # Sort by Time
        # (Optional but good for display)
    
    print(f"Đã lấy được {len(df)} sự kiện USD (UTC Today).")
    
    csv_file = "economic_calendar.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"Đã lưu dữ liệu vào {csv_file}")
    
    driver.quit()

if __name__ == "__main__":
    get_economic_calendar()

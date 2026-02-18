import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Try to fake user agent to avoid basic blocks
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error setting up driver: {e}")
        return None

def get_economic_calendar():
    driver = setup_driver()
    if not driver:
        return
    
    try:
        # Override Timezone: Force Browser to Use UTC
        # This ensures ForexFactory displays times in UTC (GMT+0)
        # So we don't need to do any complex math or guessing.
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "Etc/UTC"})
        
        # We want to scrape events for "Today" (UTC).
        # But to be safe against edge cases (midnight boundaries), let's scrape [-1, 0, +1] days.
        # Then we FILTER strictly.
        
        today_utc = datetime.utcnow().date()
        print(f"Target Date (UTC): {today_utc}")

        days_to_scrape = [
             today_utc - timedelta(days=1),
             today_utc, 
             today_utc + timedelta(days=1)
        ]
        
        all_events = []
        # Current Year Context (Hardcoded 2026 based on user context, or dynamic?)
        # Let's use 2026 as requested/observed in previous context. 
        # Ideally this should be dynamic, but FF URLs use the year.
        current_year_context = "2026"

        for d in days_to_scrape:
            # Construct URL: day=feb18.2026
            month_str = d.strftime("%b").lower()
            day_str = d.day
            year_str = d.year # Use actual year from date object
            
            day_param = f"{month_str}{day_str}.{year_str}"
            url = f"https://www.forexfactory.com/calendar?day={day_param}"
            print(f"Scraping URL: {url} (Expecting UTC times)")
            
            driver.get(url)
            
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "calendar__table"))
                )
            except:
                print(" -> Timeout or no table found.")
                continue
            
            # Scroll to load weird lazy loading if any
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find("table", class_="calendar__table")
            if not table: continue
            
            rows = table.find_all("tr", class_="calendar__row")
            print(f" -> Found {len(rows)} rows.")
            
            current_date_text = ""
            current_time_text = ""
            
            for row in rows:
                # 1. Date Header (e.g. "Thu Feb 19")
                date_cell = row.find("td", class_="calendar__date")
                if date_cell:
                    d_text = date_cell.get_text(" ", strip=True) 
                    if d_text: current_date_text = d_text 

                # 2. Currency
                currency_cell = row.find("td", class_="calendar__currency")
                currency = currency_cell.text.strip() if currency_cell else ""
                
                # Filter USD early
                if currency != "USD": continue
                    
                # 3. Time (e.g. "2:00pm") - THIS IS UTC NOW
                time_cell = row.find("td", class_="calendar__time")
                t_text = time_cell.text.strip() if time_cell else ""
                
                if t_text == "": t_text = current_time_text
                else: current_time_text = t_text
                
                if "Day" in t_text: continue # Skip All Day events for now? Or keep?
                
                # 4. Parse Date & Time to check against Target Date
                # We need to reconstruct the full datetime object to check the Date part.
                # current_date_text = "Wed Feb 18"
                # t_text = "2:00pm"
                # year = year_str (from loop)
                
                parsed_date = None
                final_time_str = t_text
                
                if "am" in t_text or "pm" in t_text:
                    try:
                        # Note: current_date_text usually doesn't have Year.
                        full_str = f"{current_date_text} {year_str} {t_text}"
                        # Parse
                        parsed_dt = datetime.strptime(full_str, "%a %b %d %Y %I:%M%p")
                        parsed_date = parsed_dt.date()
                        final_time_str = parsed_dt.strftime("%H:%M")
                    except:
                        pass
                
                # 5. STRICT FILTER
                # We only want events where the UTC Date is EXACTLY 'today_utc'
                if parsed_date:
                    if parsed_date != today_utc:
                        continue # Skip yesterday/tomorrow events
                    
                    final_date_str = parsed_dt.strftime("%a %b %d %Y")
                else:
                    # If we couldn't parse (maybe 'Tentative' or format change)
                    # Use the loop date 'd' as fallback?
                    # Safer to skip if we want strict daily report.
                    continue

                # 6. Extract other info
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
                
                # 7. Add to list
                # Deduplicate?
                unique_id = f"{final_date_str}|{final_time_str}|{event_name}|{currency}"
                if any(x['id'] == unique_id for x in all_events): continue
                
                all_events.append({
                    "id": unique_id,
                    "Date": final_date_str, 
                    "Time": final_time_str,
                    "Currency": currency,
                    "Impact": impact,
                    "Event": event_name,
                    "Actual": actual,
                    "Forecast": forecast,
                    "Previous": previous
                })
        
        # Sort by Time
        all_events.sort(key=lambda x: x['Time'])
        
        # Create DataFrame
        if not all_events:
            print("No events found for USD today (UTC).")
            # Create empty CSV with headers
            df = pd.DataFrame(columns=["Date","Time","Currency","Impact","Event","Actual","Forecast","Previous"])
        else:
            df = pd.DataFrame(all_events).drop(columns=['id'])
            print(f"Total Unique/Filtered USD Events (UTC): {len(df)}")
            print(df[['Time', 'Event']])
        
        csv_file = "economic_calendar.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"Saved to {csv_file}")
        
        return df
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    get_economic_calendar()

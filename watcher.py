import time
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from discord_notifier import DiscordNotifier
import scraper

# Load environment variables
load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def get_utc_now():
    return datetime.utcnow()

def parse_event_time(date_str, time_str):
    # date_str: "Wed Feb 18 2026"
    # time_str: "19:00"
    try:
        dt_str = f"{date_str} {time_str}"
        return datetime.strptime(dt_str, "%a %b %d %Y %H:%M")
    except Exception as e:
        # printf(f"Error parsing time: {e}")
        return None

def prepare_event_embed(row):
    # Determine Color & Icon
    color = 0xffffff # Default White
    impact_icon = "⚪"
    
    if row['Impact'] == 'High': 
        color = 0xff0000 # Red
        impact_icon = "🔴"
    elif row['Impact'] == 'Medium': 
        color = 0xffa500 # Orange
        impact_icon = "🟠"
    elif row['Impact'] == 'Low': 
        color = 0xffff00 # Yellow
        impact_icon = "🟡"

    # Title: Empty (User requested to move everything to Description)
    title = ""
    
    # Description: Time + Icon + Event Name + Table
    description = f"**{row['Time']}** {impact_icon} | **{row['Event']}**\n"
    description += f"| {'Previous':^10} | {'Forecast':^10} | {'Actual':^10} |\n"
    description += f"| {str(row['Previous']):^10} | {str(row['Forecast']):^10} | {str(row['Actual']):^10} |"
    
    return title, description, color

def main():
    print("🚀 Watcher started (6-hour window)...")
    
    # 6 Hours in seconds
    MAX_RUNTIME = 6 * 3600 
    start_time = time.time()
    
    # Track notified events to avoid spam
    notified_events = set()

    while (time.time() - start_time) < MAX_RUNTIME:
        
        # 1. Get Schedule (Potential Events)
        print("📅 Checking schedule...")
        df_schedule = scraper.get_economic_calendar()
        
        if df_schedule is None or df_schedule.empty:
            print("No events found today. Sleeping 1 hour...")
            time.sleep(3600)
            continue

        # 2. Identify Pending Events (High/Medium)
        utc_now = get_utc_now()
        pending_events = []

        for index, row in df_schedule.iterrows():
            if row['Impact'] not in ['High', 'Medium', 'Low']: continue 

            event_dt = parse_event_time(row['Date'], row['Time'])
            if not event_dt: continue
            
            time_diff = (event_dt - utc_now).total_seconds()
            unique_id = f"{row['Date']}_{row['Time']}_{row['Event']}"
            if unique_id in notified_events: continue
            
            # Check if Actual present (already released)
            has_actual = str(row['Actual']).strip() != ""
            if has_actual and str(row['Actual']) != "nan": 
                # Already released, skip
                notified_events.add(unique_id)
                continue
            
            # Pending or very recently passed (within 10 mins)
            if time_diff > -600: 
                pending_events.append({
                    "dt": event_dt,
                    "row": row,
                    "id": unique_id
                })

        if not pending_events:
            print("✅ No more pending events. Exiting.")
            break

        pending_events.sort(key=lambda x: x['dt'])
        next_event = pending_events[0]
        
        time_to_wait = (next_event['dt'] - get_utc_now()).total_seconds()
        
        # 3. Wait Logic
        if time_to_wait > 0:
            print(f"⏳ Next event: {next_event['row']['Event']} at {next_event['row']['Time']} UTC.")
            print(f"😴 Sleeping for {time_to_wait:.0f} seconds...")
            time.sleep(time_to_wait)
        else:
            print(f"⏰ Event time arrived: {next_event['row']['Event']}")

        # 4. Smart Polling
        target_time_str = next_event['row']['Time']
        events_at_this_time = [e for e in pending_events if e['row']['Time'] == target_time_str]
        
        print(f"🔄 Polling for {len(events_at_this_time)} events at {target_time_str}...")
        
        POLL_TIMEOUT = 600
        poll_start = time.time()
        
        while (time.time() - poll_start) < POLL_TIMEOUT:
            print(f"   >> Polling...")
            df_latest = scraper.get_economic_calendar()
            
            if df_latest is not None:
                still_pending = []
                for target in events_at_this_time:
                    match = df_latest[
                        (df_latest['Event'] == target['row']['Event']) & 
                        (df_latest['Time'] == target['row']['Time'])
                    ]
                    
                    if not match.empty:
                        latest_row = match.iloc[0]
                        actual_val = str(latest_row['Actual']).strip()
                        
                        if actual_val and actual_val != "nan":
                            print(f"   🎯 Data Found: {actual_val}")
                            
                            # Notify using Embed
                            if WEBHOOK_URL:
                                notifier = DiscordNotifier(WEBHOOK_URL)
                                title, desc, col = prepare_event_embed(latest_row)
                                notifier.send_embed(title, desc, color=col)
                                print("   📨 Embed sent.")
                            
                            notified_events.add(target['id'])
                        else:
                            still_pending.append(target)
                    else:
                        still_pending.append(target)
                
                events_at_this_time = still_pending
                if not events_at_this_time:
                    print("✅ All events resolved.")
                    break
            
            print("   💤 Retrying in 30s...")
            time.sleep(30)
            
    print("🏁 Watcher finished.")

if __name__ == "__main__":
    main()

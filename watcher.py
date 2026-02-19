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

def to_serif_bold(text):
    # Mapping for Mathematical Bold Serif
    # A-Z: 119808-119833 (0x1D400)
    # a-z: 119834-119859 (0x1D41A)
    # 0-9: 120782-120791 (0x1D7CE)
    
    result = ""
    for char in text:
        code = ord(char)
        if 'A' <= char <= 'Z':
            result += chr(0x1D400 + (code - ord('A')))
        elif 'a' <= char <= 'z':
            result += chr(0x1D41A + (code - ord('a')))
        elif '0' <= char <= '9':
            result += chr(0x1D7CE + (code - ord('0')))
        else:
            result += char
    return result

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

    # Title: Time + Icon + Event (Converted to Serif Bold)
    # Note: Icons and | are kept as is, only text/numbers converted ideally.
    # But simple conversion logic works fine for mixed string.
    raw_title = f"{row['Time']} | {row['Event']}"
    serif_title = to_serif_bold(raw_title)
    
    # Insert Icon back (Unicode chars shouldn't be converted by range check)
    # Or just construct: Serif(Time) + Icon + | + Serif(Event)
    
    # Let's keep it simple: Convert alphanumeric, keep others.
    # 07:30 -> 𝟎𝟕:𝟑𝟎 (Serif dict covers digits)
    
    title = f"{to_serif_bold(row['Time'])} {impact_icon} | {to_serif_bold(row['Event'])}"
    
    # Description: Code Block Grid
    h1, h2, h3 = "Previous", "Forecast", "Actual"
    v1 = str(row['Previous'])
    v2 = str(row['Forecast'])
    v3 = str(row['Actual'])

    description = "```\n"
    description += f"{h1:^10} {h2:^10} {h3:^10}\n"
    description += f"{v1:^10} {v2:^10} {v3:^10}\n"
    description += "```"
    
    # Color Logic
    actual_color_status = row.get('ActualColor', 'neutral')
    if actual_color_status == 'green': color = 0x00ff00
    elif actual_color_status == 'red': color = 0xff0000

    return title, description, color, []

def send_schedule_summary(df, webhook_url):
    """Sends a summary of all events found for the session."""
    if df.empty or not webhook_url: return

    notifier = DiscordNotifier(webhook_url)
    
    # Construct Body
    desc = ""
    for _, row in df.iterrows():
        icon = "⚪"
        if row['Impact'] == 'High': icon = "🔴"
        elif row['Impact'] == 'Medium': icon = "🟠"
        elif row['Impact'] == 'Low': icon = "🟡"
        
        # Format: 07:30 🔴 Event Name (Fcst: x.x%)
        fcst = f"(Fcst: {row['Forecast']})" if str(row['Forecast']) != 'nan' else ""
        desc += f"`{row['Time']}` {icon} **{row['Event']}** {fcst}\n"

    title = f"📅 Daily Economic Schedule ({len(df)} Events)"
    notifier.send_embed(title, desc, color=0x3498db) # Blue for Info

def send_latest_check(df, webhook_url):
    """Sends the notification for the most recent event with Actual data."""
    if df.empty or not webhook_url: return
    
    # Filter events with Actual data
    completed_events = []
    for _, row in df.iterrows():
        if str(row['Actual']).strip() != "" and str(row['Actual']) != "nan":
            completed_events.append(row)
            
    if not completed_events:
        print("ℹ️ No past events with data found to send check.")
        return

    # Get the LAST completed event (most recent)
    # Assuming df is sorted by time
    latest_event = completed_events[-1]
    
    print(f"👀 Sending Latest Event Check: {latest_event['Event']}")
    
    notifier = DiscordNotifier(webhook_url)
    title, desc, color, fields = prepare_event_embed(latest_event)
    notifier.send_embed(title, desc, color=color, fields=fields)


def main():
    print("🚀 Watcher started (6-hour window)...")
    
    # Initial Scrape for startup actions
    print("📅 Fetching initial schedule...")
    df_schedule = scraper.get_economic_calendar()
    
    if df_schedule is not None and not df_schedule.empty:
        # 0. Send Summary
        print("📨 Sending Daily Schedule Summary...")
        send_schedule_summary(df_schedule, WEBHOOK_URL)
        
        # 0.5 Send Latest Result (if any)
        print("📨 Sending Latest Data Check...")
        send_latest_check(df_schedule, WEBHOOK_URL)
    
    # 6 Hours
    MAX_RUNTIME = 6 * 3600 
    start_time = time.time()
    
    notified_events = set()

    # Pre-fill notified_events with those already having data (so we don't spam them again in the loop)
    # BUT wait, user might WANT to see the latest one in the loop? 
    # Usually the loop checks "if has_actual -> add to notified -> continue".
    # So if we run "send_latest_check", we just sent it once successfully.
    # The loop logic will handle deduplication normally.
    
    while (time.time() - start_time) < MAX_RUNTIME:
        
        # 1. Get Schedule (Refresh)
        # We can reuse df_schedule for the first iteration?
        # Let's just strictly follow the loop structure to keep state fresh.
        print("🔄 Refreshing schedule...")
        df_schedule = scraper.get_economic_calendar()
        
        if df_schedule is None or df_schedule.empty:
            print("No events found. Sleeping 1 hour...")
            time.sleep(3600)
            continue

        # 2. Identify Pending
        utc_now = get_utc_now()
        pending_events = []

        for index, row in df_schedule.iterrows():
            if row['Impact'] not in ['High', 'Medium', 'Low']: continue 

            event_dt = parse_event_time(row['Date'], row['Time'])
            if not event_dt: continue
            
            time_diff = (event_dt - utc_now).total_seconds()
            unique_id = f"{row['Date']}_{row['Time']}_{row['Event']}"
            if unique_id in notified_events: continue
            
            has_actual = str(row['Actual']).strip() != ""
            if has_actual and str(row['Actual']) != "nan": 
                notified_events.add(unique_id)
                continue
            
            if time_diff > -600: 
                pending_events.append({"dt": event_dt, "row": row, "id": unique_id})

        if not pending_events:
            print("✅ No more pending events. Exiting.")
            break

        pending_events.sort(key=lambda x: x['dt'])
        next_event = pending_events[0]
        
        time_to_wait = (next_event['dt'] - get_utc_now()).total_seconds()
        
        # 3. Wait Logic
        if time_to_wait > 0:
            print(f"⏳ Next event: {next_event['row']['Event']} at {next_event['row']['Time']}")
            print(f"😴 Sleeping {time_to_wait:.0f}s...")
            time.sleep(time_to_wait)
        else:
            # Maybe it's just happened or slightly past
            pass

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
                            print(f"   🎯 Data: {actual_val}")
                            
                            if WEBHOOK_URL:
                                notifier = DiscordNotifier(WEBHOOK_URL)
                                # Unpack 4 values now
                                title, desc, col, fields = prepare_event_embed(latest_row)
                                # Send with fields
                                notifier.send_embed(title, desc, color=col, fields=fields)
                                print("   📨 Sent.")
                            
                            notified_events.add(target['id'])
                        else:
                            still_pending.append(target)
                    else:
                        still_pending.append(target)
                
                events_at_this_time = still_pending
                if not events_at_this_time:
                    print("✅ Resolved.")
                    break
            
            time.sleep(30)
            
    print("🏁 Finished.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Fatal Error in Watcher: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

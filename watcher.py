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

def format_event_message(row):
    # Format user requested:
    # 07:30 🟠 | Core Durable Goods Orders m/m
    # 	Previous	Forecast	Actual
    # 	  5.4%		 -1.8%		-1.4%
    
    impact_icon = "⚪"
    if row['Impact'] == 'High': impact_icon = "🔴"
    elif row['Impact'] == 'Medium': impact_icon = "🟠"
    elif row['Impact'] == 'Low': impact_icon = "🟡"

    msg = f"{row['Time']} {impact_icon} | **{row['Event']}**\n"
    msg += "```\n"
    msg += f"{'Previous':^10} {'Forecast':^10} {'Actual':^10}\n"
    msg += f"{str(row['Previous']):^10} {str(row['Forecast']):^10} {str(row['Actual']):^10}\n"
    msg += "```"
    return msg

def main():
    print("🚀 Watcher started (6-hour window)...")
    
    # 6 Hours in seconds
    MAX_RUNTIME = 6 * 3600 
    start_time = time.time()
    
    # Track notified events to avoid spam
    notified_events = set()

    while (time.time() - start_time) < MAX_RUNTIME:
        
        # 1. Get Schedule (Potential Events)
        # We perform a "Schedule Scrape" to see what's coming up.
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
            # Only High/Medium
            if row['Impact'] not in ['High', 'Medium', 'Low']: continue 
            # Note: User request implies filtering relevant news. Let's keep High/Medium/Low but prioritize?
            # User example showed Low too? "07:30 🟠". Let's Watch ALL for now or stick to impact.
            # Usually users care about High/Medium. Let's include all for now to be safe.

            # Time check
            event_dt = parse_event_time(row['Date'], row['Time'])
            if not event_dt: continue
            
            # Check if event is in future (or very recent past if we missed it by seconds)
            # And within our 6-hour window?
            # Actually, logic: Find NEXT event.
            
            time_diff = (event_dt - utc_now).total_seconds()
            
            # Identify unique ID
            unique_id = f"{row['Date']}_{row['Time']}_{row['Event']}"
            if unique_id in notified_events: continue

            # If event is in the past (> 15 mins ago) and we haven't notified, 
            # maybe we missed it or it already happened. Use "Actual" check?
            # If "Actual" is empty, it's pending.
            
            has_actual = str(row['Actual']).strip() != ""
            
            if has_actual:
                # Already released, skip
                notified_events.add(unique_id)
                continue
            
            # If event is upcoming (time_diff > -600: allow 10 mins late check)
            if time_diff > -600: 
                pending_events.append({
                    "dt": event_dt,
                    "row": row,
                    "id": unique_id
                })

        if not pending_events:
            print("✅ No more pending events for today/window. Exiting.")
            break

        # Sort by time
        pending_events.sort(key=lambda x: x['dt'])
        next_event = pending_events[0]
        
        time_to_wait = (next_event['dt'] - get_utc_now()).total_seconds()
        
        # 3. Wait Logic
        if time_to_wait > 0:
            print(f"⏳ Next event: {next_event['row']['Event']} at {next_event['row']['Time']} UTC.")
            print(f"😴 Sleeping for {time_to_wait:.0f} seconds...")
            time.sleep(time_to_wait)
        else:
            print(f"⏰ Event time arrived/passed: {next_event['row']['Event']}")

        # 4. Smart Polling Logic
        # Now we poll for "Actual" data for this specific event(s) at this time.
        # Handle multiple events at same time?
        target_time_str = next_event['row']['Time']
        events_at_this_time = [e for e in pending_events if e['row']['Time'] == target_time_str]
        
        print(f"🔄 Starting Smart Polling for {len(events_at_this_time)} events at {target_time_str}...")
        
        POLL_TIMEOUT = 600 # 10 minutes
        poll_start = time.time()
        
        while (time.time() - poll_start) < POLL_TIMEOUT:
            # Re-scrape
            print(f"   >> Polling... (Eligible events: {len(events_at_this_time)})")
            df_latest = scraper.get_economic_calendar()
            
            if df_latest is not None:
                # Check each target event
                still_pending = []
                
                for target in events_at_this_time:
                    # Find in new df
                    # Match by Event Name (and Time)
                    match = df_latest[
                        (df_latest['Event'] == target['row']['Event']) & 
                        (df_latest['Time'] == target['row']['Time'])
                    ]
                    
                    if not match.empty:
                        latest_row = match.iloc[0]
                        actual_val = str(latest_row['Actual']).strip()
                        
                        if actual_val:
                            # FOUND DATA!
                            print(f"   🎯 Data Found for {target['row']['Event']}: {actual_val}")
                            
                            # Notify
                            if WEBHOOK_URL:
                                notifier = DiscordNotifier(WEBHOOK_URL)
                                message = format_event_message(latest_row)
                                notifier.send_message(message)
                                print("   📨 Notification sent.")
                            
                            notified_events.add(target['id'])
                        else:
                            still_pending.append(target)
                    else:
                        # Event disappeared? 
                        still_pending.append(target)
                
                events_at_this_time = still_pending
                
                if not events_at_this_time:
                    print("✅ All events for this time slot resolved.")
                    break
            
            # Wait before retry
            print("   💤 Data not ready. Retrying in 30s...")
            time.sleep(30)
            
        # End of Polling Loop
        # If we timed out, we just move on.
        # The events will be re-evaluated in main loop next iteration (and maybe skipped if too old).
        
    print("🏁 Watcher finished 6-hour shift.")

if __name__ == "__main__":
    main()

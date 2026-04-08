import os
import time
from dotenv import load_dotenv
import scraper
import watcher
from discord_notifier import DiscordNotifier

# Load Environment
load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def run_debug():
    print("🚀 STARTED DEBUG WATCHER...")
    print("1. Scraping data from ForexFactory (Real-time)...")
    
    # Force scrape now
    df = scraper.get_economic_calendar()
    
    if df is None or df.empty:
        print("❌ Filtered dataframe is empty. No high impact USD events?")
        print("💡 Tip: Check 'scraper.py' filter logic (lines 106+).")
        return

    print(f"✅ Found {len(df)} events.")
    
    # Try to find ANY event with Actual data to test the format
    target_row = None
    
    print("2. Searching for an event with 'Actual' data to send...")
    for index, row in df.iterrows():
        actual = str(row['Actual']).strip()
        if actual and actual != "nan":
            target_row = row
            print(f"   🎯 Found candidate: {row['Event']} ({row['Time']}) | Actual: {actual}")
            break
            
    if target_row is None:
        print("⚠️ No event with 'Actual' data found in the scraped list.")
        print("   (Maybe all events today are pending or haven't happened yet?)")
        print("   -> Attempting to send the FIRST event anyway (using 'N/A' for Actual if needed, just to test Layout).")
        target_row = df.iloc[0]

    # Prepare Notification
    print("3. Formatting Notification...")
    title, desc, color, fields = watcher.prepare_event_embed(target_row)
    
    print(f"   Title: {title}")
    print(f"   Description: \n{desc}")
    print(f"   Color: {color}")
    
    # Send
    if WEBHOOK_URL:
        print(f"4. Sending to Discord Webhook: {WEBHOOK_URL[:30]}...")
        notifier = DiscordNotifier(WEBHOOK_URL)
        notifier.send_embed(title, desc, color=color, fields=fields)
        print("✅ SENT! Please check your Discord Channel.")
    else:
        print("❌ No Webhook URL found in .env!")

if __name__ == "__main__":
    run_debug()

import scraper
import pandas as pd

print("Testing scraper import...")
try:
    df = scraper.get_economic_calendar()
    if df is not None and isinstance(df, pd.DataFrame):
        print("SUCCESS: Scraper returned a DataFrame.")
        print(df.head())
    else:
        print("FAILURE: Scraper did not return a DataFrame.")
except Exception as e:
    print(f"ERROR: {e}")

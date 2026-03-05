import time
import schedule
from datetime import datetime
import argparse

from module1_news import run_news_agent
from module2_content import process_pending_news
from module4_publisher import run_publisher

def main_loop(test_mode=False):
    print(f"[{datetime.now()}] --- Social Media Automation System Started ---")
    
    if test_mode:
        print("Running in TEST MODE. Executing pipeline once blindly (skipping schedule).")
        print("\n--- Phase 1: News Research ---")
        run_news_agent()
        print("\n--- Phase 2: Content Creation ---")
        process_pending_news()
        print("\n--- Phase 3: Publishing Agent ---")
        run_publisher()
        print("\nPipeline execution complete.")
        return

    # Define the schedule
    # Module 1: Fetch news every 6 hours
    schedule.every(6).hours.do(run_news_agent)
    
    # Module 2: Check for new fetched news every hour
    schedule.every(1).hours.do(process_pending_news)
    
    # Module 4: Check for 'Approved' items and publish them every 10 minutes
    schedule.every(10).minutes.do(run_publisher)

    print("Scheduler activated. Waiting for designated intervals...")
    print("  - News Agent: Every 6 hours")
    print("  - Content Agent: Every 1 hour")
    print("  - Publishing Agent: Every 10 minutes")
    print("(Press Ctrl+C to quit)\n")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60) # Wake up every minute to check if jobs are pending
    except KeyboardInterrupt:
        print("\nSystem gracefully shut down.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Social Media Automation Pipeline.")
    parser.add_argument("--test", action="store_true", help="Run the entire pipeline once immediately.")
    args = parser.parse_args()
    
    main_loop(test_mode=args.test)

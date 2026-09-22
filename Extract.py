import requests
import json
import time
import os

APP_ID = 1091500                               # Cyberpunk 2077
OUTPUT_FILE = "Raw_File.jsonl"                 # match your existing raw file name
STATE_FILE = "extract_state.json"              # tracks the newest review already captured
REVIEWS_PER_PAGE = 100
REQUEST_DELAY = 1.5
MAX_PAGES = 3000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def load_last_seen_timestamp():
    if not os.path.isfile(STATE_FILE):
        return 0   # no state yet = pull everything
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("last_seen_timestamp", 0)


def save_last_seen_timestamp(timestamp):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_seen_timestamp": timestamp}, f)


def fetch_review_page(cursor):
    url = f"https://store.steampowered.com/appreviews/{APP_ID}"
    params = {
        "json": 1,
        "filter": "recent",   # newest-first - required for pagination AND for the stop-early logic below
        "language": "english",
        "num_per_page": REVIEWS_PER_PAGE,
        "cursor": cursor,
    }
    response = requests.get(url, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def extract_new_reviews():
    last_seen_timestamp = load_last_seen_timestamp()
    print(f"Last seen timestamp: {last_seen_timestamp} "
          f"({'first run - pulling full history' if last_seen_timestamp == 0 else 'incremental run'})")

    cursor = "*"
    page = 0
    total_saved = 0
    newest_timestamp_this_run = last_seen_timestamp

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        while page < MAX_PAGES:
            page += 1
            data = fetch_review_page(cursor)

            if data.get("success") != 1:
                raise RuntimeError(f"API returned an error on page {page}: {data}")

            batch = data.get("reviews", [])
            if not batch:
                print("No more reviews - reached the end.")
                break

            reached_known_data = False
            for review in batch:
                review_timestamp = review.get("timestamp_created", 0)

                if review_timestamp <= last_seen_timestamp:
                    # Reviews come back newest-first, so hitting one this old means
                    # everything from here on was already captured in a previous
                    # run - stop instead of re-fetching history we already have.
                    reached_known_data = True
                    break

                f.write(json.dumps(review) + "\n")
                total_saved += 1
                newest_timestamp_this_run = max(newest_timestamp_this_run, review_timestamp)

            print(f"Page {page}: {total_saved} new reviews saved so far")

            if reached_known_data:
                print("Reached previously-captured reviews - incremental run complete.")
                break

            new_cursor = data.get("cursor")
            if not new_cursor or new_cursor == cursor:
                print("Cursor stopped advancing - stopping to avoid a loop.")
                break
            cursor = new_cursor

            time.sleep(REQUEST_DELAY)  # Crucial: pace requests, don't hammer the API

    if total_saved > 0:
        save_last_seen_timestamp(newest_timestamp_this_run)
    print(f"\nDone. Saved {total_saved} new reviews to {OUTPUT_FILE}")


if __name__ == "__main__":
    extract_new_reviews()
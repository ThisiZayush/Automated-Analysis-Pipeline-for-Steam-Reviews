import json
import re
import os
import sys
import pandas as pd

RAW_REVIEWS = "Raw_File.jsonl"                  # The raw extracted data file
TRANSFORMED_FILE = "Transformed_File.csv"       # After transformation the new file in csv


# Loading the data
def load_raw_file(path):
    reviews = []
    with open(path,"r",encoding="UTF-8") as f:
        for line in f:
            line = line.strip()
            if line:
                reviews.append(json.loads(line))
    return reviews


# Selecting only those fields from the whole review line
def flatten_reviews(reviews):
    rows = []
    for r in reviews:
        author = r.get("author", {})
        rows.append({
            "review_id":  r.get("recommendationid"),
            "timestamp_created": r.get("timestamp_created"),
            "timestamp_updated": r.get("timestamp_updated"),
            "review_text": r.get("review", ""),
            "voted_up": r.get("voted_up"),
            "votes_up": r.get("votes_up",0),
            "comment_count": r.get("comment_count",0),
            "playtime_at_review_minutes": author.get("playtime_at_review"),
            "playtime_forever_minutes": author.get("playtime_forever"),
        })
    return pd.DataFrame(rows)


def strip_bbcode(text):
    # Steam reviews support lightweight formatting tags: [b], [i], [url=..], [list], [*], etc.
    # Strip them so sentiment analysis reads plain text later, not markup noise.
    return re.sub(r"\[/?(\w+|\*)(=[^\]]*)?\]", "", text)


def clean_reviews(df):
    before = len(df)

    # Drop the duplicates reviews
    df = df.drop_duplicates(subset="review_id")

    # Text clean up: strip steam BBcode style format, extra whitespace
    df["review_text"] = df["review_text"].astype(str).apply(strip_bbcode)
    df["review_text"] = df["review_text"].str.strip()
    df["review_text"] = df["review_text"].str.replace(r"\n{2,}", "\n", regex=True)

    # Drop empty or near empty reviews
    df = df[df["review_text"].str.len() >= 10]

    # Unix timestamps -> real dates
    df["date_created"] = pd.to_datetime(df["timestamp_created"], unit="s")
    df["date_updated"] = pd.to_datetime(df["timestamp_updated"], unit="s")
    df = df.drop(columns=["timestamp_created","timestamp_updated"])

    # Playtime conversion from raw minutes to hours
    df["playtime_at_review_hours"] = (df["playtime_at_review_minutes"] / 60).round(1)
    df["playtime_forever_hours"] = (df["playtime_forever_minutes"] / 60).round(1)
    df = df.drop(columns=["playtime_at_review_minutes", "playtime_forever_minutes"])

    after = len(df)
    print(f"Clean the {RAW_REVIEWS} dowm to {after} (removed {before-after} duplicates/empites)")

    return df


def main():
    if not os.path.isfile(RAW_REVIEWS):
        print(f"Can't find the {RAW_REVIEWS}....")
        sys.exit(1)

    print(f"Loading raw reviews from {RAW_REVIEWS}....")
    raw_reviews = load_raw_file(RAW_REVIEWS)        # Now passing the extracted file to load
    print(f"Loaded {len(raw_reviews)} raw reviews")

    # Now passing the loaded data to get flatten into simple tables
    df = flatten_reviews(raw_reviews)

    # Cleaning the flatten data 
    df = clean_reviews(df)
    
    if df.empty:
        print("No reviews left after cleaning - check the raw file / field names before saving.")
        sys.exit(1)

    # Converting the json file to CSV
    df.to_csv(TRANSFORMED_FILE,index=False)
    print(f"Saved cleaned data to {TRANSFORMED_FILE}")

    print("\n--- Summary ---")
    print(f"Total reviews: {len(df)}")
    print(f"Positive (voted up): {df['voted_up'].sum()} ({df['voted_up'].mean()*100:.1f}%)")
    print(f"Date range: {df['date_created'].min().date()} to {df['date_created'].max().date()}")


if __name__ == "__main__":
    main()
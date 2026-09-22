import os
import urllib.parse
import sys
import pandas as pd
from sqlalchemy import create_engine, text

SCORED_FILE = "Sentiment_Score_File.csv"

# SQL Server connection settings
SERVER_NAME = "BAT-COMPUTER"                    # Name of the server(incase of local use "localhost")
DATABASE_NAME = "SteamReviewsAnalysis"          # Name of the database in which we want to load the data (Create this in advance)
ODBC_DRIVER = "ODBC Driver 17 for SQL Server"   # check the "ODBC Data Sources (64-bit)" app on Windows if unsure which you have

ASPECTS = ["performance", "story", "gameplay", "price", "graphics"]


# Setting up the connection with the database
def get_engine():
    odbc_str = (
        f"DRIVER={{{ODBC_DRIVER}}};"
        f"SERVER={SERVER_NAME};"
        f"DATABASE={DATABASE_NAME};"
        "Trusted_Connection=yes;"       # Windows Authentication - the local-install default
        "TrustServerCertificate=yes;"   # avoids a common SSL error: newer ODBC drivers require this for a local, self-signed instance
    )
    connection_url = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_str)}"
    return create_engine(connection_url)


# Creating the schema for the tables
def create_schema(engine):
    with engine.begin() as conn:

        # Drop child table before parent - review_aspects has a foreign key into reviews,
        # and unlike SQLite, SQL Server actually enforces that by default.
        conn.execute(text("IF OBJECT_ID('review_aspects', 'U') IS NOT NULL DROP TABLE review_aspects;"))
        conn.execute(text("IF OBJECT_ID('reviews', 'U') IS NOT NULL DROP TABLE reviews;"))

        # Review Table
        conn.execute(text("""
            CREATE TABLE reviews (
                review_id VARCHAR(50) PRIMARY KEY,
                review_text NVARCHAR(MAX),
                voted_up BIT,
                votes_up INT,
                comment_count INT,
                playtime_at_review_hours FLOAT,
                playtime_forever_hours FLOAT,
                date_created DATETIME2,
                date_updated DATETIME2,
                sentiment_compound FLOAT,
                sentiment_label VARCHAR(20),
                sentiment_neg FLOAT,
                sentiment_neu FLOAT,
                sentiment_pos FLOAT
            );
        """))

        # Review Aspect table
        conn.execute(text("""
            CREATE TABLE review_aspects (
                review_id VARCHAR(50),
                aspect VARCHAR(20),
                aspect_sentiment FLOAT,
                FOREIGN KEY (review_id) REFERENCES reviews(review_id)
            );
        """))

        conn.execute(text("CREATE INDEX idx_aspect ON review_aspects(aspect);"))


# Loading the reviews data into tables
def load_reviews_table(engine, df):
    cols = [
        "review_id", "review_text", "voted_up", "votes_up",
        "comment_count", "playtime_at_review_hours", "playtime_forever_hours",
        "date_created", "date_updated", "sentiment_compound", "sentiment_label",
        "sentiment_neg", "sentiment_neu", "sentiment_pos",
    ]

    #
    reviews_df = df[cols].copy()
    # CSVs often read these back as strings ("True"/"False") or 1/0, and forcing bool makes sure they map cleanly onto SQL Server's BIT type.
    reviews_df["voted_up"] = reviews_df["voted_up"].astype(bool)

    # Table was already created above with the exact types/keys we want -
    # "append" just inserts into it, it won't try to redefine the schema.
    reviews_df.to_sql("reviews", engine, if_exists="append", index=False)
    print(f"Loaded {len(reviews_df)} rows into 'reviews'")


# Loading the aspect reviews data into tables
def load_aspects_table(engine, df):
    frames = []

    for aspect in ASPECTS:
        mentioned_col = f"mentions_{aspect}"
        sentiment_col = f"{aspect}_sentiment"
        subset = df.loc[df[mentioned_col] == True, ["review_id", sentiment_col]].copy()
        subset = subset.rename(columns={sentiment_col: "aspect_sentiment"})
        subset["aspect"] = aspect
        frames.append(subset)

    aspects_df = pd.concat(frames, ignore_index=True)[["review_id", "aspect", "aspect_sentiment"]]
    aspects_df.to_sql("review_aspects", engine, if_exists="append", index=False)
    print(f"Loaded {len(aspects_df)} rows into review_aspects")


def main():
    if not os.path.isfile(SCORED_FILE):
        print(f"Can't find {SCORED_FILE} - run the Sentiment script first")
        sys.exit(1)

    print(f"Loading {SCORED_FILE}...")
    df = pd.read_csv(SCORED_FILE, parse_dates=["date_created", "date_updated"])
    print(f"Loaded {len(df)} scored reviews")

    engine = get_engine()
    create_schema(engine)
    load_reviews_table(engine, df)
    load_aspects_table(engine, df)  ## must run after reviews - its foreign key depends on it existing first

    print(f"\nDone. Data is in the '{DATABASE_NAME}' database on {SERVER_NAME}.")
    print("Try in SSMS: SELECT aspect, COUNT(*), AVG(aspect_sentiment) FROM review_aspects GROUP BY aspect;")


if __name__ == "__main__":
    main()
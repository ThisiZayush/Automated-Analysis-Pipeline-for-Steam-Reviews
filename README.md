# Steam Review Sentiment Pipeline

An automated ETL pipeline that extracts user reviews from the Steam Web API, cleans and transforms them, scores sentiment with a gaming-tuned NLP model, and loads the results into SQL Server for analysis in Power BI.

Built around **Cyberpunk 2077**, but the pipeline works for any Steam App ID.

---

## Overview

Steam reviews are messy: informal language, slang, sarcasm, and BBCode markup. This project turns that raw text into structured, queryable sentiment data — both **overall** sentiment per review and **aspect-based** sentiment (performance, story, gameplay, price, graphics) — so you can answer questions like *"what do people actually think of the game's performance vs. its story?"*

The pipeline runs unattended on a schedule, only pulling new reviews each time, and logs every run for debugging.

## Pipeline Architecture

```
Steam Web API
      │
      ▼
 ┌─────────┐    ┌───────────┐    ┌───────────┐    ┌─────────┐
 │ Extract │───▶│ Transform │───▶│ Sentiment │───▶│  Load   │───▶ SQL Server
 └─────────┘    └───────────┘    └───────────┘    └─────────┘
   .jsonl            .csv          scored .csv      reviews +
                                                     review_aspects
```

Orchestrated end-to-end by `Run_Pipeline.py`, which runs each stage in order, stops immediately if one fails, and writes a full log to `pipeline_log.txt`.

## Features

- **Incremental extraction** — tracks the newest review timestamp already collected and only pulls newer ones on subsequent runs, instead of re-downloading full history every time
- **Text cleaning** — strips Steam's BBCode formatting tags, removes duplicates and near-empty reviews, converts Unix timestamps to real dates
- **Custom sentiment scoring** — built on NLTK's VADER, extended with a 50+ term gaming/slang lexicon (e.g. `"cracked"`, `"mid"`, `"cashgrab"`) plus Cyberpunk-specific terms (`"choom"`, `"preem"`, `"edgerunners"`) so sentiment scoring understands the actual vocabulary reviewers use
- **Aspect-based sentiment** — keyword-matches sentences to five categories (performance, story, gameplay, price, graphics) and scores each independently, so a review can be positive overall but negative on price
- **Relational SQL Server schema** — a `reviews` table plus a `review_aspects` child table (foreign-keyed, indexed on aspect) for flexible querying
- **Automated & logged** — designed to run unattended via Windows Task Scheduler, with timestamped logs and clear failure states so a broken stage never lets bad data reach the database

## Tech Stack

| Layer | Tools |
|---|---|
| Extraction | Python, `requests`, Steam Web API |
| Transformation | `pandas`, `re` |
| Sentiment analysis | NLTK (VADER), custom lexicon |
| Storage | SQL Server, SQLAlchemy, `pyodbc` |
| Orchestration | Python (`subprocess`), Windows Task Scheduler |
| Visualization | Power BI |

## Project Structure

```
├── Bootstrap.py          # One-time setup: seeds extract_state.json from existing raw data
├── Extract.py             # Pulls new reviews from the Steam Web API
├── Transform.py           # Cleans and flattens raw JSON into a structured CSV
├── Sentiment.py           # Scores overall + aspect-based sentiment with VADER
├── Load.py                # Loads scored data into SQL Server
├── Run_Pipeline.py        # Orchestrates all four stages, with logging and failure handling
├── extract_state.json     # Tracks last-seen review timestamp (generated)
├── Raw_File.jsonl         # Raw extracted reviews (generated)
├── Transformed_File.csv   # Cleaned reviews (generated)
├── Sentiment_Score_File.csv  # Scored reviews (generated)
└── pipeline_log.txt       # Run history and error logs (generated)
```

## Database Schema

**`reviews`** — one row per review: review text, vote, votes/comments, playtime, dates, and overall sentiment scores (compound, label, neg/neu/pos).

**`review_aspects`** — one row per (review, aspect) mention, foreign-keyed to `reviews`, indexed on `aspect`, storing the aspect-specific sentiment score.

```sql
-- Example: average sentiment per aspect
SELECT aspect, COUNT(*), AVG(aspect_sentiment)
FROM review_aspects
GROUP BY aspect;
```

## Setup

1. **Install dependencies**
   ```bash
   pip install requests pandas nltk sqlalchemy pyodbc
   ```
2. **Configure SQL Server** — create the target database, and set `SERVER_NAME` / `DATABASE_NAME` in `Load.py` to match your instance.
3. **Set the Steam App ID** — update `APP_ID` in `Extract.py` for the game you want to track.
4. **(Optional) Bootstrap existing data** — if you already have a `Raw_File.jsonl`, run `Bootstrap.py` once so `Extract.py` only pulls reviews newer than what you already have.
5. **Run the pipeline**
   ```bash
   python Run_Pipeline.py
   ```

## Automation

`Run_Pipeline.py` is designed to run unattended via **Windows Task Scheduler** (or `cron` on Linux/macOS). It resolves all file paths relative to its own location, captures each stage's console output into `pipeline_log.txt`, and exits with a non-zero code on failure so a scheduler can detect and alert on failed runs.

## Dashboard

Sentiment results are connected to **Power BI** via a direct SQL Server connection, with visuals for sentiment trends over time, aspect-by-aspect comparison, and agreement between VADER's read and the reviewer's own thumbs-up/down vote.

## License

MIT

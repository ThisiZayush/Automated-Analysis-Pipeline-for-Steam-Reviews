import json

RAW_FILE = "Raw_File.jsonl"
STATE_FILE = "extract_state.json"

max_timestamp = 0
count = 0

with open(RAW_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            review = json.loads(line)
            max_timestamp = max(max_timestamp, review.get("timestamp_created", 0))
            count += 1

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump({"last_seen_timestamp": max_timestamp}, f)

print(f"Scanned {count} existing reviews.")
print(f"Bootstrapped {STATE_FILE} with last_seen_timestamp = {max_timestamp}")
print("From now on, Extract.py will only pull reviews newer than this.")
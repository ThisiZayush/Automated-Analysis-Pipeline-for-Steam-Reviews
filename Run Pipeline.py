import os
import subprocess
import sys
import time
from datetime import datetime

# Task Scheduler starts programs in C:\Windows\System32 by default, which would
# break every relative path in the stage scripts (Raw_File.jsonl, extract_state.json, ...).
# Anchoring everything to this file's own folder makes the pipeline work no matter
# where it is launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Update these to match your actual script filenames
STAGES = [
    ("Extract",   "Extract.py"),
    ("Transform", "Transform.py"),
    ("Sentiment", "Sentiment.py"),
    ("Load",      "Load.py"),
]

LOG_FILE = os.path.join(BASE_DIR, "pipeline_log.txt")


def write_log(line):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log(message):
    # Writes to both the console (useful when run by hand) and the log file
    # (essential when Task Scheduler runs it unattended).
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    write_log(line)


def run_stage(name, script_name):
    log(f"Starting stage: {name}")

    # Force UTF-8 in the child process so its output can be read back reliably
    # on Windows, regardless of the console code page.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    # sys.executable = the exact interpreter running this runner, so stages can't
    # accidentally use a different Python install (ModuleNotFoundError problems).
    # "-u" = unbuffered, so lines reach the log in the order they were printed.
    process = subprocess.Popen(
        [sys.executable, "-u", os.path.join(BASE_DIR, script_name)],
        cwd=BASE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # errors/tracebacks land in the log too
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Copy the stage's output to both console and log file as it runs
    for raw_line in process.stdout:
        line = f"    [{name}] {raw_line.rstrip()}"
        print(line, flush=True)
        write_log(line)

    returncode = process.wait()

    if returncode != 0:
        log(f"FAILED: {name} (exit code {returncode}) - stopping pipeline")
        return False

    log(f"Completed: {name}")
    return True


def main():
    # Avoid crashes if the console can't display a character
    if sys.stdout is not None:
        sys.stdout.reconfigure(errors="replace")

    log("=== Pipeline run started ===")
    start = time.time()

    for name, script_name in STAGES:
        if not run_stage(name, script_name):
            # Stop immediately on failure - don't let Transform run on a broken
            # Extract, and never let Load push incomplete data into the database.
            log("=== Pipeline run FAILED ===")
            sys.exit(1)

    elapsed_minutes = (time.time() - start) / 60
    log(f"=== Pipeline run completed successfully in {elapsed_minutes:.1f} minutes ===")


if __name__ == "__main__":
    main()
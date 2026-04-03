import argparse
import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("logs") / "chats.jsonl"


from collections import deque

import textwrap
import shutil

import time

def print_entry(e, wrap_width, term_width):
    ts = e["timestamp"][:19].replace("T", " ")
    user = f"@{e['username']}"
    msg = e["message"]
    reply = e["reply"]
    
    # Wrap content to fit terminal
    msg_wrapped = textwrap.fill(msg, width=wrap_width).replace("\n", "\n     ")
    reply_wrapped = textwrap.fill(reply, width=wrap_width).replace("\n", "\n     ")

    print(f"\033[90m[{ts}]\033[0m {user}")
    print(f"  \033[33mW:\033[0m {msg_wrapped}")
    print(f"  \033[32mR:\033[0m {reply_wrapped}")
    print("-" * term_width)

def view_logs(n: int | None, follow: bool = False):
    if not LOG_FILE.exists():
        print("no logs found ke.")
        return

    term_width = shutil.get_terminal_size((80, 20)).columns
    wrap_width = max(40, term_width - 10)

    if follow:
        # First, show the last N entries in oldest-to-newest order
        entries = deque(maxlen=n) if n else []
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
                
                print(f"\033[1mInitial {len(entries)} logs (Oldest -> Newest). Following... (Ctrl+C to stop)\033[0m")
                print("=" * term_width)
                for e in entries:
                    print_entry(e, wrap_width, term_width)
                
                # Now follow and append new ones at the bottom
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.5)
                        continue
                    try:
                        data = json.loads(line)
                        print_entry(data, wrap_width, term_width)
                    except json.JSONDecodeError:
                        continue
        except KeyboardInterrupt:
            print("\nStopped.")
            return
        except Exception as e:
            print(f"Error: {e}")
            return
    else:
        entries = deque(maxlen=n) if n else []
        try:
            with open(LOG_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error: {e}")
            return

        print(f"\033[1mLog Viewer - {len(entries)} Entries (Oldest First)\033[0m")
        print("=" * term_width)
        # Oldest first (natural order)
        for e in entries:
            print_entry(e, wrap_width, term_width)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="view chat logs")
    parser.add_argument("-n", type=int, default=20, help="show last N entries (default: 20)")
    parser.add_argument("-f", "--follow", action="store_true", help="follow log output (like tail -f)")
    args = parser.parse_args()
    view_logs(args.n, args.follow)

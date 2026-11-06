"""Create starter AI declaration ledgers from Git history. Run once by a maintainer."""

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DECLARATIONS_DIR = Path(".ai-declarations")
AUTONOMY_LEVELS = ("none", "autocomplete", "co-piloted", "agentic")
LOGIN_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,38})")
NOREPLY_PATTERN = re.compile(r"(?:\d+\+)?([^@]+)@users\.noreply\.github\.com")
# Lowercase Git author names whose GitHub login differs; extend when a new identity appears.
LOGIN_OVERRIDES = {
    "dominik r laetsch": "drl",
    "dom laetsch": "drl",
    "richard challis": "rjchallis",
    "dinesh a": "heisdinesh",
    "rohan barsagade": "rohan-b-84",
}


def login_for(email, name):
    """Map a commit identity to a GitHub login, using all identities for one person."""
    key = name.strip().lower()
    if key in LOGIN_OVERRIDES:
        return LOGIN_OVERRIDES[key]
    noreply = NOREPLY_PATTERN.fullmatch(email.strip().lower())
    if noreply:
        return noreply.group(1)
    return key.replace(" ", "-")


def main():
    DECLARATIONS_DIR.mkdir(exist_ok=True)
    log = subprocess.run(
        ["git", "log", "--format=%ae%x00%an"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    commit_counts = Counter()
    for line in log.splitlines():
        email, _, name = line.partition("\x00")
        commit_counts[login_for(email, name)] += 1

    print("Generating starter ledgers in .ai-declarations/ (commits per login):")
    for login, count in commit_counts.most_common():
        if "[bot]" in login or "github-actions" in login:
            continue
        if not LOGIN_PATTERN.fullmatch(login):
            print(f"Skipping '{login}': not a valid GitHub login.")
            continue

        path = (DECLARATIONS_DIR / f"{login}.json").resolve()
        if path.parent != DECLARATIONS_DIR.resolve():
            print(f"Skipping '{login}': path escapes {DECLARATIONS_DIR}.")
            continue
        if path.exists():
            print(f"Skipping {login}: ledger already exists.")
            continue

        print(f"{count:>5}  {login}")
        ledger = {
            "username": login,
            "totals": {level: 0 for level in AUTONOMY_LEVELS},
            # Historical commits, assumed human-authored; not part of PR totals.
            "baseline_commits": count,
            "history": [
                {
                    "pr_number": 0,
                    "pr_url": "N/A",
                    "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "declared_autonomy": "none",
                    "tools_used": [],
                    "note": "Historical repository import baseline",
                }
            ],
        }
        path.write_text(json.dumps(ledger, indent=2) + "\n")

    print("Done! Starter files created in .ai-declarations/")


if __name__ == "__main__":
    main()

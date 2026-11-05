import json
import os
import subprocess

# 1. Ensure the declarations directory exists
os.makedirs(".ai-declarations", exist_ok=True)

# 2. Get a list of all contributors and their total commit counts from Git history
cmd = "git log --format='%ae|%an' | sort | uniq -c"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

print("🚀 Generating machine-readable starter files...")

for line in result.stdout.strip().split("\n"):
    if not line:
        continue

    # Parse out commit counts and user details
    parts = line.strip().split(maxsplit=1)
    commit_count = int(parts[0])
    email_name = parts[1].split("|")

    # Clean up the username to match GitHub login styles (lowercase, no spaces)
    username = email_name[1].lower().replace(" ", "-")

    # Skip standard CI bots
    if "github-actions" in username or "dependabot" in username:
        continue

    json_path = f".ai-declarations/{username}.json"

    # Only create a starter file if it doesn't already exist
    if not os.path.exists(json_path):
        starter_data = {
            "username": username,
            "totals": {
                "none": commit_count,  # Assume all historical commits were human-authored baseline
                "autocomplete": 0,
                "co-piloted": 0,
                "agentic": 0,
            },
            "history": [
                {
                    "pr_number": 0,
                    "pr_url": "N/A",
                    "date": "2026-11-05",
                    "declared_autonomy": "none",
                    "tools_used": [],
                    "note": "Historical repository import baseline",
                }
            ],
        }

        with open(json_path, "w") as jf:
            json.dump(starter_data, jf, indent=2)

print("✅ Done! Starter files created in .ai-declarations/")

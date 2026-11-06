"""Record a merged pull request's AI declaration and refresh the README metrics table."""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DECLARATIONS_DIR = Path(".ai-declarations")
PR_RECORDS_DIR = DECLARATIONS_DIR / "prs"
README_PATH = Path("README.md")
AUTONOMY_LEVELS = ("none", "autocomplete", "co-piloted", "agentic")
LOGIN_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,38})")
METADATA_PATTERN = re.compile(
    r"<!-- AI-METADATA: autonomy=([\w-]+) phases=([\w,]*) tools=([^\n]*?)\s*-->"
)
METRICS_PATTERN = re.compile(
    r"(<!-- AI_PER_USER_METRICS_START -->).*?(<!-- AI_PER_USER_METRICS_END -->)",
    re.DOTALL,
)
TABLE_HEADER = (
    "| Developer | Pure Human | Autocomplete | Co-Piloted | Agentic | Last Active Tool |\n"
    "| :-------- | :--------: | :----------: | :--------: | :-----: | :--------------- |\n"
)


def parse_declaration(body):
    """Return (autonomy, phases, tools) from the PR body metadata tag."""
    match = METADATA_PATTERN.search(body)
    if not match:
        print("No AI-METADATA tag found in PR body; recording as none.")
        return "none", [], []
    autonomy = match.group(1).lower()
    if autonomy not in AUTONOMY_LEVELS:
        print(f"Unsupported autonomy '{autonomy}' in PR metadata; recording as none.")
        return "none", [], []
    phases = [phase for phase in match.group(2).split(",") if phase]
    tools = [tool.strip() for tool in match.group(3).split(",") if tool.strip()]
    return autonomy, phases, tools


def load_baseline(login):
    """Hand-maintained baseline; the tally never rewrites it."""
    path = DECLARATIONS_DIR / f"{login}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {
        "username": login,
        "totals": {level: 0 for level in AUTONOMY_LEVELS},
        "history": [],
    }


def load_pr_records():
    records = {}
    for path in sorted(PR_RECORDS_DIR.glob("*.json")):
        entry = json.loads(path.read_text())
        records.setdefault(entry["username"], []).append(entry)
    return records


def build_ledger(login, baseline, pr_entries):
    """Merge a baseline ledger with the per-PR records for one user."""
    ledger = {
        "username": login,
        "totals": dict(baseline["totals"]),
        "history": list(baseline["history"]),
    }
    for entry in sorted(pr_entries, key=lambda item: item["pr_number"]):
        autonomy = entry["declared_autonomy"]
        ledger["totals"][autonomy] = ledger["totals"].get(autonomy, 0) + 1
        ledger["history"].append(entry)
    return ledger


def last_tool(ledger):
    if not ledger["history"]:
        return "None"
    latest = ledger["history"][-1]
    if latest.get("declared_autonomy", "none") == "none":
        return "None"
    return ", ".join(latest.get("tools_used", [])) or "Unknown AI"


def render_table(ledgers):
    rows = []
    for login, ledger in sorted(ledgers, key=lambda item: item[0]):
        totals = ledger["totals"]
        rows.append(
            f"| @{login} | {totals.get('none', 0)} | {totals.get('autocomplete', 0)} "
            f"| {totals.get('co-piloted', 0)} | {totals.get('agentic', 0)} | {last_tool(ledger)} |\n"
        )
    return TABLE_HEADER + "".join(rows)


def load_all_ledgers():
    records = load_pr_records()
    logins = {path.stem for path in DECLARATIONS_DIR.glob("*.json")} | set(records)
    return [
        (login, build_ledger(login, load_baseline(login), records.get(login, [])))
        for login in sorted(logins)
    ]


def update_readme(table):
    text = README_PATH.read_text()
    if not METRICS_PATTERN.search(text):
        sys.exit("Metrics markers missing from README.md.")
    block = f"\n\n### Contributor Development Breakdown\n\n{table}\n"
    updated = METRICS_PATTERN.sub(
        lambda match: match.group(1) + block + match.group(2), text, count=1
    )
    README_PATH.write_text(updated)


def main():
    login = os.environ["PR_AUTHOR"].lower()
    if login.endswith("[bot]"):
        print(f"Skipping bot author {login}.")
        return
    if not LOGIN_PATTERN.fullmatch(login):
        sys.exit(f"Refusing unexpected GitHub login '{login}'.")

    autonomy, phases, tools = parse_declaration(os.environ.get("PR_BODY", ""))
    pr_number = int(os.environ["PR_NUMBER"])
    PR_RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    path = PR_RECORDS_DIR / f"{login}-{pr_number}.json"
    if path.exists():
        print(f"PR #{pr_number} is already recorded; skipping.")
    else:
        entry = {
            "username": login,
            "pr_number": pr_number,
            "pr_url": os.environ["PR_URL"],
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "declared_autonomy": autonomy,
            "phases": phases,
            "tools_used": tools,
        }
        path.write_text(json.dumps(entry, indent=2) + "\n")

    update_readme(render_table(load_all_ledgers()))


if __name__ == "__main__":
    main()

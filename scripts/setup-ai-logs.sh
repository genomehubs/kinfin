#!/bin/bash
set -e

HOOK_PATH=".git/hooks/pre-push"

echo "Installing local Git pre-push hook for AI logging..."

cat << 'EOF' > "$HOOK_PATH"
#!/bin/bash
STATE_FILE=".ai-state.json"

# Exit instantly if no AI state file exists (Clean human developer branch)
if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

if ! command -v gh &> /dev/null; then
    echo "Warning: .ai-state.json detected but 'gh' CLI is not found or authenticated."
    exit 0
fi

# Extract metadata fields safely
AUTONOMY=$(python3 -c "import json, os; print(json.load(open('$STATE_FILE')).get('autonomy_level', 'none'))")
PHASES=$(python3 -c "import json; print(','.join(json.load(open('$STATE_FILE')).get('phases', [])))")
TOOLS=$(python3 -c "import json; print(','.join(json.load(open('$STATE_FILE')).get('tools', [])))")
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)

if [ -n "$BRANCH" ]; then
    echo "AI declaration detected ($AUTONOMY). Appending metadata safely to branch tracking..."
    # Attach tracking variables cleanly into the PR body context dynamically
    gh pr edit "$BRANCH" --body "$(gh pr view "$BRANCH" --json body -q .body 2>/dev/null)\n\n<!-- AI-METADATA: autonomy=$AUTONOMY phases=$PHASES tools=$TOOLS -->" 2>/dev/null || true
fi
EOF

chmod +x "$HOOK_PATH"
echo "Hook successfully installed at $HOOK_PATH. (Non-AI users remain unaffected!)"
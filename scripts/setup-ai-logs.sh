#!/bin/bash
set -e

HOOK_PATH=".git/hooks/pre-push"
LOCAL_HOOK_PATH=".git/hooks/pre-push.local"
MARKER="# AI-LOGGING-HOOK"

echo "Installing local Git pre-push hook for AI logging..."

if [ -f "$HOOK_PATH" ] && ! grep -q "$MARKER" "$HOOK_PATH"; then
    if [ -e "$LOCAL_HOOK_PATH" ]; then
        echo "Error: $LOCAL_HOOK_PATH already exists. Move or merge it before running this script."
        exit 1
    fi
    echo "Existing pre-push hook kept as $LOCAL_HOOK_PATH and will still run."
    mv "$HOOK_PATH" "$LOCAL_HOOK_PATH"
fi

cat << 'EOF' > "$HOOK_PATH"
#!/bin/bash
# AI-LOGGING-HOOK
STATE_FILE=".ai-state.json"
LOCAL_HOOK=".git/hooks/pre-push.local"

record_ai_declaration() {
    # Clean human developer branch: no state file, nothing to record
    [ -f "$STATE_FILE" ] || return 0

    if ! command -v gh &> /dev/null; then
        echo "Warning: .ai-state.json detected but 'gh' CLI is not found or authenticated."
        return 0
    fi

    BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null) || return 0

    if ! PR_BODY=$(gh pr view "$BRANCH" --json body -q .body 2>/dev/null); then
        echo "AI declaration not recorded: no pull request for '$BRANCH' yet. Open the PR and push again."
        return 0
    fi

    AUTONOMY=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('autonomy_level', 'none'))")
    PHASES=$(python3 -c "import json; print(','.join(json.load(open('$STATE_FILE')).get('phases', [])))")
    TOOLS=$(python3 -c "import json; print(','.join(json.load(open('$STATE_FILE')).get('tools', [])))")

    # Replace any tag added by an earlier push so only the latest declaration remains
    PR_BODY=$(printf '%s' "$PR_BODY" | sed '/<!-- AI-METADATA:/d')
    NEW_BODY=$(printf '%s\n\n<!-- AI-METADATA: autonomy=%s phases=%s tools=%s -->' "$PR_BODY" "$AUTONOMY" "$PHASES" "$TOOLS")

    echo "AI declaration detected ($AUTONOMY). Updating pull request metadata..."
    gh pr edit "$BRANCH" --body "$NEW_BODY" >/dev/null 2>&1 || echo "Warning: failed to update the pull request body."
}

record_ai_declaration

if [ -x "$LOCAL_HOOK" ]; then
    exec "$LOCAL_HOOK" "$@"
fi
exit 0
EOF

chmod +x "$HOOK_PATH"
echo "Hook successfully installed at $HOOK_PATH. (Non-AI users remain unaffected!)"
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
    # Hooks run non-interactively, so gh must not prompt for a repository
    export GH_PROMPT_DISABLED=1

    BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null) || return 0

    # The PR may live in a different repo than origin (fork workflow), so try each GitHub remote
    REPO=""
    for remote in origin $(git remote); do
        URL=$(git remote get-url "$remote" 2>/dev/null) || continue
        case "$URL" in *github.com*) ;; *) continue ;; esac
        CANDIDATE=$(printf '%s' "$URL" | sed -E 's#^(ssh://git@|git@|https?://)github\.com[:/]##; s#\.git$##')
        if gh pr view "$BRANCH" -R "$CANDIDATE" --json number >/dev/null 2>&1; then
            REPO="$CANDIDATE"
            break
        fi
    done
    # Fall back to the gh default repository when no GitHub remote has the PR
    if [ -z "$REPO" ] && gh pr view "$BRANCH" --json number >/dev/null 2>&1; then
        REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)
    fi
    if [ -z "$REPO" ]; then
        echo "AI declaration not recorded: no pull request for '$BRANCH' yet. Open the PR and push again."
        return 0
    fi
    PR_NUMBER=$(gh pr view "$BRANCH" -R "$REPO" --json number -q .number 2>/dev/null)

    AUTONOMY=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('autonomy_level', 'none'))")
    PHASES=$(python3 -c "import json; print(','.join(json.load(open('$STATE_FILE')).get('phases', [])))")
    TOOLS=$(python3 -c "import json; print(','.join(json.load(open('$STATE_FILE')).get('tools', [])))")

    echo "AI declaration detected ($AUTONOMY). Updating pull request metadata..."
    # Read the body just before writing so edits made since the lookup are kept
    PR_BODY=$(gh pr view "$PR_NUMBER" -R "$REPO" --json body -q .body 2>/dev/null) || return 0
    # Replace any tag added by an earlier push so only the latest declaration remains
    PR_BODY=$(printf '%s' "$PR_BODY" | sed '/<!-- AI-METADATA:/d')
    NEW_BODY=$(printf '%s\n\n<!-- AI-METADATA: autonomy=%s phases=%s tools=%s -->' "$PR_BODY" "$AUTONOMY" "$PHASES" "$TOOLS")
    # gh pr edit fails on gh 2.62 (deprecated Projects classic query), so use the REST API
    gh api -X PATCH "repos/$REPO/pulls/$PR_NUMBER" -f body="$NEW_BODY" >/dev/null 2>&1 || echo "Warning: failed to update the pull request body."
}

record_ai_declaration

if [ -x "$LOCAL_HOOK" ]; then
    exec "$LOCAL_HOOK" "$@"
fi
exit 0
EOF

chmod +x "$HOOK_PATH"
echo "Hook successfully installed at $HOOK_PATH. (Non-AI users remain unaffected!)"
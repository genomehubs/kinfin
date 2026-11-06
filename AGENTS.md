# AI Code Governance Protocol

This repository tracks AI usage in pull requests.

Before completing any coding task, check for a `.ai-state.json` file in the repository root and create or update it:

1. If it does not exist, create it. If it exists, keep its entries and add yours if missing.
2. Set the fields:
   - `autonomy_level`: one of `none`, `autocomplete`, `co-piloted`, `agentic`.
   - `phases`: any of `planning`, `core_logic`, `testing` that apply.
   - `tools`: append your tool name, e.g. `"GitHub Copilot"` or `"Claude Code"`.
3. If the user describes how AI was used, follow their description over your own.
4. Do not commit `.ai-state.json`. It is git-ignored.

Example:

```json
{
  "autonomy_level": "agentic",
  "phases": ["core_logic", "testing"],
  "tools": ["Claude Code"]
}
```

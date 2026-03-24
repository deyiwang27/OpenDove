# PR Cycle Skill
1. Ensure working branch is based on latest `main`
2. Run full test suite before creating PR
3. Create PR with descriptive title and body
4. If CI fails, delegate fix to CodeX MCP with explicit branch name:
   ```sh
   claude -p "CI failed with these errors: $(cat ci-output.log). Fix the failing tests. Branch from main, do not reuse stale branches. Delegate to CodeX MCP if available." \
     --allowedTools "Edit,Read,Bash,mcp__codex__codex"
   ```
5. Verify CI passes, then request review

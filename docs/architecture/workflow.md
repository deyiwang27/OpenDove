# OpenDove — Development Workflow

Every piece of work follows this sequence, no exceptions.

## Step-by-step

### 1. Create a GitHub Issue
Before any code is written, open an issue describing the work:
- **Title:** short, imperative (e.g. "Implement PostgreSQL task store")
- **Body:** scope, deliverables, success criteria
- **Labels:** `enhancement`, `bug`, etc. as appropriate

```bash
gh issue create --title "..." --body "..." --label enhancement
```

### 2. Create a Feature Branch off `main`
Always branch from `main`, never from another feature branch:

```bash
git checkout main && git pull
git checkout -b feat/issue-{number}-short-description
```

### 3. Hand off to CodeX / Implement
Reference the issue number in the CodeX prompt so commits link back to it.

### 4. Commit — reference the issue
```
feat: implement X (#42)
```

### 5. Push and Open PR
```bash
git push -u origin feat/issue-{number}-short-description
gh pr create --title "..." --body "Closes #42"
```

### 6. Review, update progress doc, merge

---

## Roles in this repo

| Who | Does what |
|---|---|
| Architect (Claude) | Defines tech strategy, writes issues, reviews CodeX output |
| CodeX | Implements code and unit tests within the branch |
| CI | Lints + runs tests on every push |

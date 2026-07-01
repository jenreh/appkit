---
name: release
description: Bump version, generate an AI-written changelog, and publish a GitHub release. Use when the user says "release", "publish", or "bump version".
disable-model-invocation: true
allowed-tools: Bash, AskUserQuestion
---

# Release

Ask the user which version bump to apply, then run `task release:build`.

## Step 1 — ask

Use `AskUserQuestion` to ask:

**Question:** "Which version component should be bumped?"
**Header:** "Version bump"
**Options:**
- `patch` — backwards-compatible bug fixes and minor improvements (Recommended)
- `minor` — new backwards-compatible features
- `major` — breaking changes

## Step 2 — confirm current version

```bash
grep '^version = ' pyproject.toml | cut -d '"' -f2
```

Show the user: "Current version is X.Y.Z — bumping **[choice]** will release X.Y.Z+1. Proceed?"

If they say no, stop.

## Step 3 — run the release

```bash
task release:build -- <choice>
```

Stream the output so the user can see progress. The task will:
1. Bump the version in all tracked files
2. Commit and push
3. Generate an AI-written changelog from commits since the last tag
4. Create a GitHub release with that changelog

## Step 4 — report

After the task completes, show the new version and the GitHub release URL from the output.

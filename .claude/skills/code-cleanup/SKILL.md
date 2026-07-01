---
name: code-cleanup
description: Refactor and simplify Python files modified in the current session — minimal diff, clean code principles, then lint/format/typecheck. Use when the user asks to clean up, simplify, or refactor code.
disable-model-invocation: true
allowed-tools: Read, Edit, Bash, Agent, mcp__code-reasoning__code-reasoning, mcp__plugin_context7_context7__query-docs, mcp__plugin_context7_context7__resolve-library-id
---

# Code Cleanup

## Target files

If `$ARGUMENTS` is provided, use those files. Otherwise, run:

```bash
git diff --name-only HEAD && git ls-files --others --exclude-standard
```

Filter the output to `.py` files only — those are the files to clean up.
If no modified Python files are found, report that and stop.

## Rules

- **Minimal diff** — change only what clearly improves the file; do not restructure things that already work.
- **No new features** — preserve all existing behavior exactly.
- **Per-file scope** — do not modify files outside the target list unless an import must be fixed.

## What to apply (per file)

- Remove dead code, unused imports, redundant comments, and unnecessary variables.
- Simplify overly complex conditionals; prefer early returns over deep nesting.
- Break functions > 20 lines into focused, well-named helpers — but only when the split is obvious.
- Replace verbose loops with list/dict/set comprehensions or generator expressions where readable.
- Ensure every function and method has a type annotation.
- No `print` statements — use `logging` (default level: `logger.debug`).
- No f-strings in logger calls: `log.info("x: %s", x)` not `log.info(f"x: {x}")`.
- If a file exceeds 1000 lines after refactoring, split it and update imports accordingly.

## Process

1. Determine the target file list as described above and show it to the user.
2. For each file: read it, identify improvements, apply as a single focused edit pass.
3. After all edits: run `task format && task lint && task typecheck` and fix any issues.
4. Summarize what changed per file (one line per change group).

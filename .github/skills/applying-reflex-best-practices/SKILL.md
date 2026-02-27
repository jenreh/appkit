---
name: applying-reflex-best-practices
description: Applies Reflex.dev best practices when building, reviewing, or refactoring Python web apps using the Reflex framework. Use when writing Reflex components, state classes, event handlers, or when setting up a new Reflex project.
license: MIT
metadata:
  author: jens-rehpoehler
  version: "1.0"
---

# Applying Reflex Best Practices

## Quick reference

**Architecture**: One file per page, substates per feature, business logic in event handlers only.
**State**: Type all vars, prefix private vars with `_`, use `@rx.var(cache=True)` for heavy derivations.
**Events**: Use `yield` for streaming, `@rx.background` for async I/O.
**Performance**: Use `rx.foreach` and `rx.cond` — never bare Python `if` inside components.

## Workflow

Copy this checklist when scaffolding or reviewing a Reflex app:

Reflex Review Progress:
[ ] Step 1: Verify project structure
[ ] Step 2: Audit state design
[ ] Step 3: Review event handlers
[ ] Step 4: Check component patterns
[ ] Step 5: Validate rxconfig.py


**Step 1: Verify project structure**

Each page should be a separate module. No business logic in `app.py`.
See [references/project-structure.md](references/project-structure.md) for canonical layout.

**Step 2: Audit state design**

All state vars must be typed. Private/server-only vars use `_` prefix.
See [references/state-management.md](references/state-management.md) for patterns and examples.

**Step 3: Review event handlers**

Long I/O tasks must use `@rx.background`. Use `yield` for incremental UI updates.
Avoid blocking the event queue with synchronous network or DB calls.

**Step 4: Check component patterns**

Use `rx.foreach` for lists, `rx.cond` for conditionals. Never use bare Python `if` statements
inside component functions — they won't react to state changes.

**Step 5: Validate rxconfig.py**

Ensure `api_url` is set explicitly. Use `rx.Env.PROD` for production builds.
Pin the Reflex version in `requirements.txt` or `pyproject.toml`.

## Decision tree

**Building a new feature?** → Follow "Scaffold workflow" below
**Reviewing existing code?** → Follow "Audit workflow" below

### Scaffold workflow
1. Create a substate class in `states/<feature>_state.py`
2. Create the page in `pages/<feature>.py`
3. Register the page in `app.py` with `app.add_page()`
4. Wire event handlers to UI components

### Audit workflow
1. Check for untyped state vars → add type annotations
2. Check for Python `if` in components → replace with `rx.cond`
3. Check for synchronous I/O in event handlers → wrap with `@rx.background`
4. Check for computed vars without caching → add `cache=True` where safe

## Detailed references

**State patterns & substate design**: See [references/state-management.md](references/state-management.md)
**Performance optimization**: See [references/performance.md](references/performance.md)
**Project structure & naming**: See [references/project-structure.md](references/project-structure.md)

---
applyTo: "**"
description: "Main Copilot instructions for the appkit project - Reflex-Mantine component library with comprehensive development workflow and architecture guidelines"
---

# AppKit — Reflex-Mantine Component Library

**A comprehensive Reflex wrapper library for Mantine UI components with production-ready examples.**

> **Purpose:** Guide GitHub Copilot & Copilot Chat to align suggestions with our tech stack, workflows, and quality bars.
> **Stacks:** Python 3.13 · Reflex (UI) · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic · FastMCP · LangChain

---

## 1) Golden Rules

1. **Think → Memory → Tools → Code → Memory.** Start with step-by-step reasoning (using the tool code-reasoning); **search Memory first**; pick tools; code minimal diff; **write learnings back to Memory**.
2. **Tests are truth.** On failures: **fix code first**. Change tests only if they clearly diverge from spec.
3. **Small, safe changes.** Prefer smallest viable diff; add tests for new behavior **before** code. Keep it as simple as possible!
4. **Consistency > cleverness.** Follow this file's SOPs and stack idioms.
5. **Memory multiplies.** Persist decisions, patterns, error signatures, and proven fixes.
6. **Files ≤ 1000 lines.** No Python file may exceed 1000 lines of code. When a file approaches or exceeds this limit, refactor using clean code principles (see §5).
7. Do NOT generate extensive documentation, summaries or comments unless explicitly requested.
8. Do NOT use `--autogenerate` for new Alembic migrations; write them manually.
9. Do NOT use `cat` to create new files; ALWAYS use the available tools!
10. When logging, user **logger.debug** as the default level; use logger.info for important runtime events; reserve logger.warning/error for actual issues. **NEVER use `print` for logging.**

> Rule of thumb: prefer *local* changes over cross-module refactors.

---

## 2) Task Bootstrap Pattern

```markdown
<!-- plan:start
goal: <one line clear goal>
constraints:
- Python 3.13; Reflex UI; FastAPI; SQLAlchemy 2.0; Alembic; Pydantic; appkit_mantine;
- logging: no f-strings in logger calls
- files ≤ 1000 lines; apply design patterns where appropriate
- minimal diff; add/adjust tests first
definition_of_done:
- tests pass; coverage ≥ 80% (non-Reflex classes & Reflex states); lint/type checks clean; memory updated
steps:
1) Search Memory for "<keywords>"
2) Draft/adjust failing test to capture expected behavior
3) Implement minimal code change
4) Run task test; iterate until green
5) Update Memory: decisions, patterns, error→fix
plan:end -->
```

---

## 3) Tooling Decision Matrix

| Situation | Primary | Secondary | Store to Memory |
|---|---|---|---|
| API/pattern uncertainty | **Context7** | — | Canonical snippet + link; edge cases |
| Ecosystem bug/issue | **DuckDuckGo** | — | Minimal repro; versions; workaround |
| Repeated test failure | **Memory (search)** | Context7 | Error signature → fix; root cause |
| New feature scaffold | **Context7** | — | How‑to snippet; checklist |
| House style/tooling | **This file** | Context7 | Checklist results |

**Prefer official docs; widen via web search when cross-version issues arise.**

---

## 4) SOP — Development Workflow

**Task Runner:** Use `task` commands (via `Taskfile.dist.yml`) instead of `make`.

### Prepare
1. **Memory first:** search for prior solutions and patterns.
2. **Reasoning plan:** use the *Task Bootstrap Pattern*.
3. **Sync tools:** `task sync` (uses **uv**, Python 3.13).
4. **Baseline:** `task test` to snapshot current failures.

### Triage Failures
- Read the **first** failing assertion; map to spec.
- If tests match spec → fix code. If tests diverge → document and adjust spec/tests (after approval).
- Add/adjust unit tests to codify expected behavior.

### Implement (Minimal Diff)
- Tests-first for new behavior.
- Use only approved stacks.
- Apply design patterns where appropriate (see §5).
- **NEVER use `print` for logging.** Always use the `logging` module.
- **Logging (no f-strings):**
  ```python
  import logging
  log = logging.getLogger(__name__)
  log.info("Loaded items: %d", count)      # ✅
  # log.info(f"Loaded items: {count}")     # ❌
  ```

### Quality Gates
- Lint/format/type: `task lint`, `task format`.
- Tests: `task test` with coverage ≥ **80%** for non-Reflex classes and Reflex states.

### Commit & PR
- Conventional Commits (`feat:`, `fix:`, `refactor:`…).
- PR must include: description, `Closes #123`, UI screenshots, migration rationale.

### Learn
- Reflect; extract learnings; write to **Memory**.

---

## 5) Python Code & Testing

Python code style, clean code principles, design patterns, and testing strategy are maintained in the **writing-python-code** skill. Key rules:

- **Python 3.13** only; deps via **uv**; line length **88** chars.
- **No f-strings in logger calls** — use parameterized logging.
- **Files ≤ 1000 lines** — refactor via clean code patterns.
- **Coverage ≥ 80%** for non-Reflex classes and Reflex State classes.
- **Type annotations** on all functions and methods.

---

## 6) Reflex Best Practices

General Reflex patterns are maintained in the **applying-reflex-best-practices** skill. The following are **appkit-specific** rules:

- **Substates & Mixins:** Split large state classes into feature-based mixins. State vars stay on the main class; methods are organized by concern in separate mixin classes.
- **Background Task Event Chaining:** Background tasks cannot be called directly from other event handlers — always yield the class method reference: `yield MyState.background_task`.
- **rx.cond operators:** Use `&` and `|` instead of `and`/`or`.
- **Database Access:** Do not use `rx.session()` in background processors, callbacks, or pure Python utilities. Use `appkit_commons.database.session_manager.get_session_manager().session()` instead.

---

## 7) Using appkit_mantine Components

Component API, event handler patterns, and usage examples are maintained in the **using-appkit-mantine** skill. Key project-wide rules:

- **Import:** `import appkit_mantine as mn` — Mantine 8.3.14.
- **Never redeclare inherited props** — base classes (`MantineComponentBase` → `MantineLayoutComponentBase` → `MantineInputComponentBase`) provide ~40 common props. Only define component-specific props.
- **MantineProvider** is auto-injected at priority 44 — no manual wrapping needed.

---

## 8) Security & Config Hygiene

- No credentials in code/history; use `.env` locally, Key Vault in prod.
- Prefer non-secret YAML; override with env `__` pattern.
- Parameterized logs; avoid sensitive values.
- Access Pydantic `SecretStr` fields via `.get_secret_value()`.
- Update vulnerable deps promptly; document CVE-driven updates in commits and **Memory**.

---

## 9) Search SOPs

- **Context7 first** for framework truths; cite sources in **Memory**.
- **DuckDuckGo** for cross-version issues; prefer official docs, well-known repos.
- Capture only the **final answer** in **Memory**: minimal snippet + rationale + version pins + link.

---

## 10) Pre‑PR Checklist

- [ ] Tests added/updated; all green
- [ ] Coverage ≥ 80% for non-Reflex classes and Reflex states
- [ ] Lint/format/type checks pass (`task format && task lint`)
- [ ] No Python file exceeds 1000 lines
- [ ] Design patterns applied where appropriate
- [ ] Migrations reviewed & documented
- [ ] **Memory updated** (decisions, patterns, error→fix links)
- [ ] PR description complete; links/screenshots added

---

## 11) Available Skills

| Skill | Purpose |
|---|---|
| `writing-python-code` | Python 3.13 code style, logging, type annotations, design patterns, testing strategy |
| `applying-reflex-best-practices` | Reflex architecture, state design, event handlers, component patterns |
| `using-appkit-mantine` | Mantine UI component API, inheritance hierarchy, event handlers, forms, layouts |
| `testing-reflex-state` | Pytest unit tests for Reflex State classes — event handlers, computed vars, substates |
| `multi-stage-dockerfile` | Optimized multi-stage Dockerfiles, layer caching, security hardening, healthchecks |

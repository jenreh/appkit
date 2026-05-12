# AppKit — Reflex-Mantine Component Library

> **Stacks:** Python 3.14 · Reflex.dev (UI) · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic · FastMCP · LangChain

---

## 1) Golden Rules

1. **Think → Memory → Tools → Code → Memory.** Use code-reasoning; search Memory and claude-context first; minimal diff; write learnings back.
2. **Tests are truth.** Failures → fix code first. Change tests only if clearly wrong spec.
3. **Minimal diff.** Add tests before code. Keep simple.
4. **Consistency > cleverness.** Follow SOPs and stack idioms.
5. **Memory multiplies.** Persist decisions, patterns, error signatures, proven fixes.
6. **Files ≤ 1000 lines.** Exceed → refactor (see §5).
7. No extensive docs/summaries/comments unless requested.
8. No `--autogenerate` for Alembic migrations; write manually.
9. No `cat` to create files; use tools.
10. Log default: `logger.debug`. Important events: `logger.info`. Issues only: `logger.warning/error`. **No `print`.**
11. **Caveman skill** applies to all writes here.

> Prefer *local* changes over cross-module refactors.

---

## 2) Task Bootstrap Pattern

```markdown
<!-- plan:start
goal: <one line clear goal>
constraints:
- Python 3.14; Reflex UI; FastAPI; SQLAlchemy 2.0; Alembic; Pydantic; appkit_mantine;
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
| --- | --- | --- | --- |
| API/pattern uncertainty | **Context7** | — | Canonical snippet + link; edge cases |
| Ecosystem bug/issue | **DuckDuckGo** | Context7 | Minimal repro; versions; workaround |
| Repeated test failure | **Memory (search)** | Context7 | Error signature → fix; root cause |
| New feature scaffold | **Context7** | — | How‑to snippet; checklist |
| House style/tooling | **This file** | Context7 | Checklist results |

Prefer official docs; widen via web search for cross-version issues.

---

## 4) SOP — Development Workflow

**Task Runner:** `task` (via `Taskfile.dist.yml`), not `make`.

### Prepare

1. Memory first — search prior solutions.
2. Reasoning plan — Task Bootstrap Pattern.
3. `task sync` (uv, Python 3.13).
4. `task test` — snapshot current failures.

### Triage Failures

- Read first failing assertion; map to spec.
- Tests match spec → fix code. Diverge → document; adjust spec/tests (after approval).
- Add/adjust unit tests to codify expected behavior.

### Implement (Minimal Diff)

- Tests-first for new behavior. Approved stacks only. Apply design patterns (see §5).
- **No `print`.** Use `logging` module.
- **No f-strings in logger calls:**

  ```python
  import logging

  log = logging.getLogger(__name__)
  log.info("Loaded items: %d", count)  # ✅
  # log.info(f"Loaded items: {count}") # ❌
  ```

### Quality Gates

- `task lint`, `task format`.
- `task test` — coverage ≥ **80%** non-Reflex classes & Reflex states.

### Commit & PR

- Conventional Commits (`feat:`, `fix:`, `refactor:`…).
- PR: description, `Closes #123`, UI screenshots, migration rationale.

### Learn → write to **Memory**

---

## 5) Python Code & Testing

Full rules in **writing-python-code** skill. Key:

- Python 3.14; uv; line length **88**.
- No f-strings in logger calls.
- Files ≤ 1000 lines.
- Coverage ≥ 80% non-Reflex classes & State classes.
- Type annotations on all functions/methods.

---

## 6) Reflex Best Practices

Full rules in **reflex-state-and-architecture** skill. Appkit-specific:

- **Substates & Mixins:** State vars on main class; methods split by concern in mixins.
- **Background Task Chaining:** Yield class method ref: `yield MyState.background_task`.
- **rx.cond operators:** `&` and `|`, not `and`/`or`.
- **DB Access:** No `rx.session()` in background/callbacks/utils. Use `appkit_commons.database.session_manager.get_session_manager().session()`.

---

## 7) appkit_mantine Components

Full API in **appkit-mantine-reference** skill. Rules:

- `import appkit_mantine as mn` — Mantine 9.2.0.
- Never redeclare inherited props — `MantineComponentBase` → `MantineLayoutComponentBase` → `MantineInputComponentBase` provide ~40 common props.
- `MantineProvider` auto-injected at priority 44 — no manual wrap.

---

## 8) Security & Config

- No credentials in code/history; `.env` local, Key Vault prod.
- Non-secret YAML; env `__` override pattern.
- Parameterized logs; no sensitive values.
- `SecretStr` → `.get_secret_value()`.
- Update vulnerable deps; document CVE-driven updates in commits & Memory.

---

## 9) Search SOPs

- **Context7 first** for framework truths; cite in Memory.
- **DuckDuckGo** for cross-version issues; prefer official docs.
- Store only final answer: minimal snippet + rationale + version pins + link.

---

## 10) Pre‑PR Checklist

- [ ] Tests added/updated; all green
- [ ] Coverage ≥ 80% non-Reflex classes & Reflex states
- [ ] `task format && task lint` pass
- [ ] No file > 1000 lines
- [ ] Design patterns applied
- [ ] Migrations reviewed & documented
- [ ] Memory updated (decisions, patterns, error→fix)
- [ ] PR description complete; links/screenshots added

---

## 11) Skills

| Skill | Purpose |
| --- | --- |
| `writing-python-code` | Python 3.14 style, logging, type annotations, design patterns, testing |
| `reflex-state-and-architecture` | State design, event handlers, background tasks, form validation, page factory, service registry, repo pattern, DB models, architecture |
| `appkit-mantine-reference` | Full API for appkit_mantine components — inputs, layout, overlays, charts, data display, navigation |
| `testing-reflex-state` | Pytest unit tests for Reflex State — event handlers, computed vars, substates |
| `multi-stage-dockerfile` | Optimized multi-stage Dockerfiles, layer caching, security, healthchecks |

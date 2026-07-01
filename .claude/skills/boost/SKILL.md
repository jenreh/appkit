---
name: boost
description: Use when the user wants to refine, sharpen, or expand a rough idea into a detailed implementation prompt — before any code gets written. Trigger on /boost, "refine this prompt", "turn this into a prompt", "help me specify", "what do I need to think through before implementing", "can you make this more detailed", rough feature ideas the user explicitly wants help scoping (not implementing). Also trigger when user says "boost this" or hands you a vague feature description and asks for a proper prompt or spec. Do NOT trigger for direct implementation requests, debugging questions, code reviews, or architectural questions where the user is not asking for a refined prompt.
allowed-tools: Read, Bash, WebSearch, WebFetch, Agent, TodoWrite, EnterPlanMode, ExitPlanMode, mcp__code-reasoning__code-reasoning, mcp__duckduckgo__search, mcp__plugin_context7_context7__query-docs, mcp__plugin_context7_context7__resolve-library-id
---

# Boost — Prompt Refinement Workflow

Help the user turn a rough idea or vague request into a precise, detailed implementation plan prompt. Do NOT write or generate any implementation code. Your output is always a refined prompt — not the solution itself.

## Workflow

### 0. Enter plan mode

Call `EnterPlanMode` immediately. This enforces the no-code constraint at the tool level and ensures the final refined prompt is delivered through the plan approval interface.

### 1. Understand the raw request

Read what the user gave you. If it's a vague idea ("I want to add auth"), that's fine — start there. If it's a half-written prompt, work from it.

Ask yourself:
- What is the user actually trying to build or change?
- What's still unclear or underspecified?

### 2. Explore the project

Use available tools to build context before asking the user anything:

- **Memory MCP** (`memory/*`, if available): query first — the user may have prior decisions, preferences, or architectural notes stored from past sessions that directly inform this task. Search for relevant entities (project name, framework, patterns, past decisions on similar features).
- **Read** key files: `CLAUDE.md`, `README.md`, entry points, relevant modules touched by the task
- **Bash/Glob/Grep**: find related code, existing patterns, current architecture
- **Reasoning MCP** (`code-reasoning/*`, if available): use extended thinking when the task involves non-obvious trade-offs, complex dependency chains, or ambiguous scope — e.g. "should this live in the service layer or the router?", "what migration strategy fits this schema?". Don't use it for simple lookups.
- **WebSearch**: look up relevant library APIs, best practices, recent changes if the task involves third-party tooling
- **context7 / upstash MCP** (if available): fetch up-to-date framework docs for any libraries involved (e.g. Reflex, FastAPI, SQLModel, Mantine)

Don't ask the user things you can find yourself. Memory and reasoning give you two advantages: memory surfaces what the user already decided so you don't ask again; reasoning helps you resolve ambiguity without guessing.

### 3. Ask targeted clarifying questions

Only ask what you couldn't determine from exploration. Keep it focused — 2–5 questions max. Examples of good questions:

- "Should this work for unauthenticated users too, or is it gated behind login?"
- "Is there an existing error handling pattern in this project I should follow, or define a new one?"
- "What's the acceptance criterion — unit tests, integration tests, or just manual verification?"

Avoid asking things already answerable from the codebase or docs.

### 4. Produce the refined prompt

Once you have enough context, write the improved prompt to the plan file. Structure it clearly:

```
## Task
[One-paragraph description of what needs to be built/changed and why]

## Context
[Relevant existing code, patterns, dependencies, constraints discovered during exploration]

## Requirements
[Numbered list of specific, verifiable requirements]

## Deliverables
[What files/functions/tests should exist when done]

## Success criteria
[How to verify the task is complete — commands to run, behavior to observe]

## Out of scope
[Explicit exclusions to prevent scope creep]
```

Adapt sections to the task — not every section applies to every task.

Then call `ExitPlanMode`. The plan approval interface becomes the iteration loop — the user can reject and request adjustments, which brings you back to this step.

### 5. Iterate

If the user rejects the plan and requests changes, update the plan file and call `ExitPlanMode` again. Repeat until approved.

## Rules

- **Never write implementation code.** You produce prompts, not solutions.
- **Prefer concrete over vague.** "Add JWT auth to the `/api/users` route" beats "add auth".
- **Surface constraints explicitly.** If the project uses a specific pattern or library, the prompt should say so.
- **Keep it actionable.** Another Claude instance reading this prompt should be able to execute it without asking follow-up questions.

# Clean Code & Design Patterns

## File size limit: 1000 lines

No Python file may exceed 1000 lines. When approaching the limit, refactor using the strategies below.

## Refactoring strategies

| Strategy | When to use | Example |
|---|---|---|
| **Extract Class** | A class has multiple responsibilities | Split `ThreadState` into mixins (`ModelSelectionMixin`, `MessageProcessingMixin`, etc.) |
| **Extract Module** | A file contains logically independent groups | Move validators, helpers, constants into separate modules |
| **Mixin / Composition** | A large state class needs decomposition while preserving a single inheritance chain | Reflex State mixins |
| **Strategy Pattern** | Multiple interchangeable algorithms | Processor classes (`OpenAIProcessor`, `PerplexityProcessor`) behind a common interface |
| **Repository Pattern** | Data access mixed with business logic | `BaseRepository` → specific repositories per entity |
| **Service Layer** | Business logic spread across handlers | Extract into service classes (`FileCleanupService`, `ThreadService`) |

## Clean code principles

- **Single Responsibility:** Each class/module has one reason to change.
- **Open/Closed:** Extend behavior through new classes, not modifying existing ones.
- **Dependency Inversion:** Depend on abstractions (protocols/ABCs), not concrete implementations.
- **DRY:** Extract shared logic into base classes, mixins, or utility modules.
- **Narrow Interfaces:** Prefer small, focused interfaces over large ones.
- **Composition over Inheritance:** Favor object composition; use inheritance only for true "is-a" relationships.

## Recommended design patterns

| Pattern | Use Case | Project Example |
|---|---|---|
| **Strategy** | Swappable algorithms (LLM processors, secret providers) | `OpenAIChatCompletionsProcessor`, `SecretProvider` |
| **Repository** | Database access abstraction | `BaseRepository`, `ThreadRepository` |
| **Factory** | Complex object construction | `ChunkFactory`, test data factories |
| **Observer** | Event-driven state updates | Reflex event handlers, `on_change` callbacks |
| **Template Method** | Shared workflow with customizable steps | `MantineComponentBase._get_custom_code()` |
| **Adapter** | Wrapping third-party APIs | Mantine component wrappers around React components |
| **Decorator** | Cross-cutting concerns | `@authenticated()`, `@requires_role()` |
| **Builder** | Step-by-step object construction | Configuration assembly via YAML + env + secrets |

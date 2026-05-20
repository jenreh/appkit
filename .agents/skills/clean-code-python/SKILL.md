---
name: clean-code-python
description: >
  Enforce Clean Code Developer (CCD) architecture and software quality principles
  when writing or refactoring Python code. Apply automatically whenever you generate
  new Python code, refactor existing Python, design modules or class hierarchies, or
  review Python architecture — even when the user doesn't mention "clean code" or
  "architecture" explicitly. Covers all four CCD grades: Orange (SRP, SoC, SLA,
  conventions), Yellow (ISP, DIP, LSP, information hiding, least astonishment),
  Green (OCP, Tell Don't Ask, Law of Demeter), Blue (YAGNI, design-first, component
  orientation). Triggers on: "write a class", "add a service", "refactor this",
  "how should I structure", "implement feature X", and any Python file editing task.
---

# Clean Code Python

Apply these principles whenever writing or refactoring Python code. Don't narrate
the framework to the user — just produce code that embodies these values. Use the
self-review checklist before presenting any non-trivial code.

## Before writing code

Think through: what is the single responsibility of this component? What are its
dependencies? What will callers need from it? Design the interface and type
signatures before the body. Only implement what the current requirement demands.

---

## Principles

### SRP — Single Responsibility Principle

One class, one reason to change. If a class touches persistence AND domain logic
AND notifications, split it.

```python
# Bad: three responsibilities in one class
class User:
    def save(self) -> None: ...          # persistence
    def send_welcome_email(self) -> None: ...  # notifications
    def validate_email(self) -> bool: ...  # domain rule

# Good: one class per responsibility
class User: ...              # domain model only
class UserRepository: ...    # persistence
class UserMailer: ...        # notifications
```

### SoC — Separation of Concerns

Cross-cutting concerns (logging, caching, auth, retries) belong in decorators or
middleware, not scattered inline inside business methods.

```python
# Bad: logging woven into business logic
def get_user(user_id: int) -> User:
    log.info("Fetching user %d", user_id)
    user = db.query(User).get(user_id)
    log.info("Fetched %s", user.name)
    return user

# Good: concern at the boundary, not the body
@log_call
def get_user(user_id: int) -> User:
    return repo.get(user_id)
```

### SLA — Single Level of Abstraction

Every line in a function should live at the same conceptual level. Don't mix raw
SQL with domain calls or HTTP requests with UI logic.

```python
# Bad: two levels in one function
def process_order(order_id: int) -> None:
    row = db.execute("SELECT * FROM orders WHERE id=?", [order_id]).fetchone()
    order = Order(id=row[0], total=Decimal(row[1]))
    send_confirmation_email(order.customer_email)

# Good: uniform level of abstraction
def process_order(order_id: int) -> None:
    order = order_repo.get(order_id)
    notifier.send_confirmation(order)
```

### DIP — Dependency Inversion Principle

High-level modules must not depend on concrete low-level classes. Depend on
`Protocol` or ABC; inject via constructor. This also makes unit testing trivial.

```python
from typing import Protocol

class UserRepository(Protocol):
    def get(self, user_id: int) -> User: ...
    def save(self, user: User) -> None: ...

class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo  # injected — never instantiated here
```

### ISP — Interface Segregation Principle

Prefer narrow `Protocol` definitions over fat ABCs. A caller should never be
forced to depend on methods it doesn't use.

```python
# Bad: every reader must implement write/delete
class DataStore(ABC):
    def read(self, key: str) -> bytes: ...
    def write(self, key: str, data: bytes) -> None: ...
    def delete(self, key: str) -> None: ...

# Good: segregated protocols
class Readable(Protocol):
    def read(self, key: str) -> bytes: ...

class Writable(Protocol):
    def write(self, key: str, data: bytes) -> None: ...
```

### LSP — Liskov Substitution Principle

Subtypes must honor the parent contract: same preconditions, same postconditions,
no narrowed exceptions. Inheritance models "behaves-as", not "is-structurally-similar".

```python
from typing import override

class Notifier:
    def send(self, message: str) -> None: ...

class EmailNotifier(Notifier):
    @override
    def send(self, message: str) -> None:
        # Must accept same input range and produce equivalent outcome
        self._smtp.send(message)
```

### Information Hiding

Expose the minimal public API. Use `_` prefix for internals. Declare module
contracts with `__all__`. Callers should depend on the interface, not implementation
details.

```python
__all__ = ["PaymentProcessor"]   # module contract

class PaymentProcessor:
    def charge(self, amount: Decimal) -> Receipt: ...   # public

    def _validate_card(self) -> bool: ...               # internal
    def _call_gateway(self) -> dict[str, object]: ...   # internal
```

### OCP — Open/Closed Principle

Open for extension, closed for modification. Add behavior by plugging in new
implementations, not by editing existing `if/elif` chains.

```python
# Bad: modify source to add a discount type
def calculate_discount(user: User, price: Decimal) -> Decimal:
    if user.tier == "premium":
        return price * Decimal("0.8")
    elif user.tier == "student":
        return price * Decimal("0.9")
    return price

# Good: extend by adding a new strategy
class DiscountStrategy(Protocol):
    def apply(self, price: Decimal) -> Decimal: ...

DISCOUNTS: dict[str, DiscountStrategy] = {
    "premium": PremiumDiscount(),
    "student": StudentDiscount(),
}

def calculate_discount(tier: str, price: Decimal) -> Decimal:
    return DISCOUNTS.get(tier, NullDiscount()).apply(price)
```

### Tell, Don't Ask

Tell objects what to do; don't interrogate their state to make decisions outside
them. Objects own their own state transitions.

```python
# Bad: external code manages the object's state
if order.status == "pending" and order.total > 0:
    order.status = "confirmed"
    order.confirmed_at = datetime.now()

# Good: the object encapsulates the transition
order.confirm()
```

### Law of Demeter

A method may call: methods on `self`, on its parameters, on objects it creates,
on its direct attributes. Avoid chaining into objects you were handed.

```python
# Bad: drilling through the object graph
amount = order.customer.wallet.primary_card.limit.amount

# Good: Customer exposes what callers need
amount = order.customer.available_credit()
```

### Principle of Least Astonishment

Components behave exactly as their names imply. Properties and query methods never
mutate state. Command methods don't return computed values with hidden side effects.

```python
# Bad: property with a side effect — caller doesn't expect this
@property
def total(self) -> Decimal:
    self._recalculate()   # surprise!
    return self._total

# Good: pure query
@property
def total(self) -> Decimal:
    return self._total

# Mutations are explicit commands, not hidden queries
def recalculate_total(self) -> None:
    self._total = sum(item.price for item in self.items)
```

### YAGNI — You Ain't Gonna Need It

Implement only what the current requirement demands. No optional parameters "for
future flexibility", no abstract base classes with a single implementation, no
plugin systems that aren't yet needed.

> If you find yourself writing `# reserved for later use`, delete it.

### Design Before Implementation

Write the type signature, the `Protocol` definition, or the function docstring
before the body. Thinking through types and contracts first surfaces design
problems cheaply — before code exists to defend.

### Component Orientation

Group related functionality into cohesive modules. A module's `__all__` is its
contract. Internal helpers that don't belong to the public contract are
`_prefixed` or live in a `_internal` submodule.

---

## Python quick-reference

| Principle | Preferred Python tool |
|-----------|----------------------|
| Minimal interfaces | `typing.Protocol` |
| Pure data containers | `@dataclass(frozen=True)` or Pydantic `BaseModel` |
| Dependency injection | Constructor params typed as `Protocol` |
| Strategy / OCP | `Protocol` + dict dispatch or `functools.singledispatch` |
| Cross-cutting concerns | Decorators, context managers |
| Module contract | `__all__` |
| Override safety | `@typing.override` (Python 3.12+) |
| Avoid mutable defaults | Never `def f(items=[])` — use `None` sentinel |

---

## Self-review checklist

Run through this before presenting non-trivial code:

- [ ] Each class has exactly one reason to change (SRP)
- [ ] Dependencies injected, never instantiated inline (DIP)
- [ ] No fat ABC — use narrow `Protocol` per caller need (ISP)
- [ ] Subtypes honor parent contract (LSP)
- [ ] `_` prefix on all internals; `__all__` set on public modules
- [ ] No `if isinstance` / `if type ==` chains — use Protocol or dispatch (OCP)
- [ ] No deep attribute chains like `a.b.c.d()` (LoD)
- [ ] Queries/properties are free of side effects (Least Astonishment)
- [ ] Tell objects what to do rather than reading and externally mutating state (TDA)
- [ ] Cross-cutting concerns in decorators/middleware, not inline
- [ ] Every function body stays at one abstraction level (SLA)
- [ ] No speculative parameters, abstractions, or layers (YAGNI)
- [ ] Interface designed before implementation (Design-first)

"""Comprehensive examples for the MarkdownPreview component."""

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class MarkdownExampleState(rx.State):
    """State for markdown preview examples."""

    # Example content
    basic_markdown: str = """# Hello World

This is a **bold** text and this is *italic*.

## Lists

### Unordered List
- Item 1
- Item 2
  - Nested item 2.1
  - Nested item 2.2
- Item 3

### Ordered List
1. First item
2. Second item
3. Third item

## Tables
| Name     | Age | City        |
|----------|-----|-------------|
| Alice    | 30  | New York    |
| Bob      | 25  | San Francisco|
| Charlie  | 35  | Los Angeles |

## Links and Images
[Visit Reflex](https://reflex.dev)

## Blockquotes
> This is a blockquote
> It can span multiple lines

## Code
Inline code: `print("Hello World")`

---

Horizontal rule above."""

    code_examples: str = """# Code Highlighting

## Python
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate fibonacci
result = fibonacci(10)
print(f"Result: {result}")
```

## Line Highlighting
```python {2,4-6}
def example():
    print("This line is highlighted")
    x = 10
    y = 20
    z = x + y
    return z
```

## With Line Numbers
```python showLineNumbers
class MyClass:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value
```
"""

    mermaid_examples: str = """# Mermaid Diagrams

## Sequence Diagram
```mermaid
sequenceDiagram
    Alice->>John: Hello John, how are you?
    loop Healthcheck
        John->>John: Fight against hypochondria
    end
    Note right of John: Rational thoughts!
    John-->>Alice: Great!
    John->>Bob: How about you?
    Bob-->>John: Jolly good!
```

## Gantt Chart
```mermaid
gantt
    title Project Timeline
    dateFormat  YYYY-MM-DD
    section Phase 1
    Task 1           :a1, 2024-01-01, 30d
    Task 2           :after a1, 20d
    section Phase 2
    Task 3           :2024-02-01, 25d
    Task 4           :20d
```
"""

    katex_examples: str = r"""# KaTeX Math

## Inline Math
The famous equation is `$$ E = mc^2 $$` discovered by Einstein.

The quadratic formula is `$$ x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} $$`.

## Block Math
```katex
c = \pm\sqrt{a^2 + b^2}
```

```katex
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
```

```katex
\begin{bmatrix}
a & b \\
c & d
\end{bmatrix}
```

## Complex Equations
```katex
\frac{d}{dx}\left( \int_{a}^{x} f(u)\,du\right)=f(x)
```

```katex
\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}
```
"""

    security_examples: str = """# Security Testing

## Strict Mode (All HTML sanitized)
This should be **safe** but HTML is stripped.

<script>alert('XSS Attack!')</script>

<img src="x" onerror="alert('XSS')">

## Standard Mode (Basic sanitization)
This is **safe** with allowed HTML.

<div style="color: blue;">Styled content</div>

## None Mode (Unsafe - for testing only)
⚠️ **Warning**: This mode allows all HTML and is unsafe for untrusted content!

<button onclick="alert('Clicked')">Don't click in production!</button>
"""

    github_alerts: str = """# GitHub Alerts

> [!NOTE]
> Useful information that users should know, even when skimming content.

> [!TIP]
> Helpful advice for doing things better or more easily.

> [!IMPORTANT]
> Key information users need to know to achieve their goal.

> [!WARNING]
> Urgent info that needs immediate user attention to avoid problems.

> [!CAUTION]
> Advises about risks or negative outcomes of certain actions.
"""

    custom_styling: str = """# Custom Styling with HTML Comments

## Centered Large Title
<!--rehype:style=display: flex; height: 150px; align-items: center;
justify-content: center; font-size: 48px;-->

## Colored Text
Markdown **Supports** <!--rehype:style=color: red;-->**Styling**
<!--rehype:style=color: blue;-->

## Styled Block
<!--rehype:style=background: #f0f0f0; padding: 20px; border-radius: 8px;
border-left: 4px solid #007bff;-->
This entire paragraph has custom styling applied via HTML comments.
You can use any CSS properties!

## Footnotes
Here is a simple footnote[^1].

With some additional text after it.

[^1]: My reference note.
"""

    current_example: str = "basic"
    current_security: str = "standard"

    def set_show_source(self, value: bool) -> None:
        self.show_source = value

    def set_current_security(self, value: str) -> None:
        self.current_security = value


def example_section(
    title: str,
    content: str,
    enable_mermaid: bool = False,
    enable_katex: bool = False,
    security_level: str = "standard",
) -> rx.Component:
    """Create a styled example section."""
    return rx.box(
        rx.box(
            rx.heading(title, size="6", margin_bottom="4"),
            mn.markdown_preview(
                source=content,
                enable_mermaid=enable_mermaid,
                enable_katex=enable_katex,
                security_level=security_level,
            ),
            padding="20px",
            border="1px solid var(--gray-6)",
            border_radius="8px",
            background_color="var(--color-panel)",
        ),
        width="100%",
        margin_bottom="8",
    )


def example_tabs() -> rx.Component:
    """Create tabbed interface for examples."""
    return rx.tabs.root(
        rx.tabs.list(
            rx.tabs.trigger("Basic", value="basic"),
            rx.tabs.trigger("Code", value="code"),
            rx.tabs.trigger("Mermaid", value="mermaid"),
            rx.tabs.trigger("KaTeX", value="katex"),
            rx.tabs.trigger("Security", value="security"),
            rx.tabs.trigger("Alerts", value="alerts"),
            rx.tabs.trigger("Styling", value="styling"),
        ),
        rx.tabs.content(
            example_section(
                "Basic Markdown",
                MarkdownExampleState.basic_markdown,
            ),
            value="basic",
        ),
        rx.tabs.content(
            example_section(
                "Code Highlighting",
                MarkdownExampleState.code_examples,
            ),
            value="code",
        ),
        rx.tabs.content(
            example_section(
                "Mermaid Diagrams",
                MarkdownExampleState.mermaid_examples,
                enable_mermaid=True,
            ),
            value="mermaid",
        ),
        rx.tabs.content(
            example_section(
                "KaTeX Math",
                MarkdownExampleState.katex_examples,
                enable_katex=True,
            ),
            value="katex",
        ),
        rx.tabs.content(
            rx.vstack(
                rx.heading("Security Levels Comparison", size="6", margin_bottom="4"),
                rx.text(
                    "Compare how different security levels handle "
                    "potentially dangerous content:",
                    margin_bottom="4",
                ),
                rx.hstack(
                    rx.button(
                        "Strict",
                        on_click=MarkdownExampleState.set_current_security("strict"),
                        variant="soft",
                        color_scheme=rx.cond(
                            MarkdownExampleState.current_security == "strict",
                            "blue",
                            "gray",
                        ),
                    ),
                    rx.button(
                        "Standard",
                        on_click=MarkdownExampleState.set_current_security("standard"),
                        variant="soft",
                        color_scheme=rx.cond(
                            MarkdownExampleState.current_security == "standard",
                            "blue",
                            "gray",
                        ),
                    ),
                    rx.button(
                        "None",
                        on_click=MarkdownExampleState.set_current_security("none"),
                        variant="soft",
                        color_scheme=rx.cond(
                            MarkdownExampleState.current_security == "none",
                            "blue",
                            "gray",
                        ),
                    ),
                    spacing="2",
                    margin_bottom="4",
                ),
                rx.box(
                    mn.markdown_preview(
                        source=MarkdownExampleState.security_examples,
                        security_level=MarkdownExampleState.current_security,
                    ),
                    padding="20px",
                    border="1px solid var(--gray-6)",
                    border_radius="8px",
                    background_color="var(--color-panel)",
                ),
                width="100%",
                align="start",
            ),
            value="security",
        ),
        rx.tabs.content(
            example_section(
                "GitHub Alerts",
                MarkdownExampleState.github_alerts,
            ),
            value="alerts",
        ),
        rx.tabs.content(
            example_section(
                "Custom Styling & Footnotes",
                MarkdownExampleState.custom_styling,
            ),
            value="styling",
        ),
        default_value="basic",
        width="100%",
    )


@navbar_layout(
    route="/markdown-preview",
    title="Markdown Preview Examples",
    navbar=app_navbar(),
    with_header=False,
)
def markdown_preview_examples() -> rx.Component:
    """Main page demonstrating MarkdownPreview features."""
    return rx.fragment(
        mn.mermaid_zoom_script(),  # Enable click-to-zoom for Mermaid diagrams
        rx.container(
            rx.vstack(
                rx.heading(
                    "MarkdownPreview Component Examples",
                    size="8",
                    margin_bottom="2",
                ),
                rx.text(
                    "Comprehensive demonstration of markdown rendering capabilities",
                    size="4",
                    color="gray",
                    margin_bottom="6",
                ),
                rx.callout.root(
                    rx.callout.icon(rx.icon("info")),
                    rx.callout.text(
                        "This component wraps react-markdown-preview with "
                        "GitHub-flavored markdown, mermaid diagrams, KaTeX math, "
                        "and configurable security. Try switching between tabs "
                        "to see different features! Click on Mermaid diagrams to zoom."
                    ),
                    margin_bottom="6",
                ),
                example_tabs(),
                spacing="4",
                width="100%",
            ),
            max_width="1200px",
            padding="4",
        ),
    )

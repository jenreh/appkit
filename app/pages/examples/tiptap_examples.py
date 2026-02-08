"""Mantine RichTextEditor (Tiptap) Examples Page.

Demonstrates various use cases and features of the RichTextEditor component.
"""

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar


class TiptapState(rx.State):
    """State for Tiptap editor examples."""

    # Simple editor content
    simple_content: str = (
        "<p>This is a simple rich text editor. Try formatting some text!</p>"
    )

    # Controlled editor content
    controlled_content: str = """<h2 style="text-align: center;">Welcome to
    Mantine Rich Text Editor</h2>
<p>This editor demonstrates <strong>controlled mode</strong> where content is
synced with Reflex state.</p>
<p>You can use:</p>
<ul>
<li><strong>Bold</strong>, <em>italic</em>, <u>underline</u> formatting</li>
<li>Lists (ordered and unordered)</li>
<li><mark>Highlighted text</mark></li>
<li>Links and more!</li>
</ul>"""

    # Minimal toolbar content
    minimal_toolbar_content: str = """<p>This editor has a <strong>minimal toolbar
    </strong> with only basic formatting controls.</p>"""

    # Custom toolbar content
    custom_toolbar_content: str = """<h2>Custom Toolbar Configuration</h2>
<p>This editor demonstrates custom toolbar groups!</p>"""

    # Color picker example content
    color_content: str = """<p>Select text and use the color picker to
    <span style="color: #fa5252">change</span> <span style="color: #228be6">text</span>
    <span style="color: #40c057">colors</span>!</p>"""

    # Minimal content
    minimal_content: str = ""

    # Code example
    code_content: str = """<p>You can write code inline with <code>backticks</code>
    or use code blocks:</p>
<pre><code>def hello_world():
    print("Hello from Mantine RichTextEditor!")</code></pre>"""

    # Readonly content
    readonly_content: str = """<h3>This editor is read-only</h3>
<p>The content cannot be edited, but you can select and copy text.</p>
<p>This is useful for displaying formatted content.</p>"""

    def update_simple_content(self, html: str) -> None:
        """Update simple editor content."""
        self.simple_content = html

    def update_controlled_content(self, html: str) -> None:
        """Update controlled editor content."""
        self.controlled_content = html

    def update_minimal_toolbar_content(self, html: str) -> None:
        """Update minimal toolbar editor content."""
        self.minimal_toolbar_content = html

    def update_custom_toolbar_content(self, html: str) -> None:
        """Update custom toolbar editor content."""
        self.custom_toolbar_content = html

    def update_color_content(self, html: str) -> None:
        """Update color editor content."""
        self.color_content = html

    def update_minimal_content(self, html: str) -> None:
        """Update minimal editor content."""
        self.minimal_content = html

    def reset_content(self) -> None:
        """Reset all editors to default content."""
        self.simple_content = "<p>Content has been reset!</p>"
        self.controlled_content = "<p>Content has been reset!</p>"
        self.minimal_toolbar_content = "<p>Content has been reset!</p>"
        self.custom_toolbar_content = "<p>Content has been reset!</p>"
        self.color_content = "<p>Content has been reset!</p>"
        self.minimal_content = ""


@navbar_layout(
    route="/tiptap",
    title="Rich Select Examples",
    navbar=app_navbar(),
    with_header=False,
)
def tiptap_page() -> rx.Component:
    """Main Tiptap examples page."""
    return mn.container(
        mn.stack(
            mn.title("Mantine RichTextEditor (Tiptap)", order=1),
            mn.text(
                "Comprehensive WYSIWYG editor based on Tiptap with full "
                "formatting support.",
                size="lg",
                c="gray",
            ),
            rx.link(
                "← Back to Home",
                href="/",
                size="3",
            ),
            # Simple editor with default toolbar
            mn.title("Rich Text Editor", order=2, mt="lg"),
            mn.text(
                "Full-featured editor with pre-configured toolbar, min/max "
                "height, and sticky toolbar.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.simple_content,
                on_update=TiptapState.update_simple_content,
                placeholder="Start typing...",
                sticky_toolbar=True,
                sticky_offset="0px",
                styles={"content": {"minHeight": "100px", "maxHeight": "160px"}},
                width="100%",
            ),
            mn.text(
                "Current content length: "
                + rx.cond(
                    TiptapState.simple_content,
                    TiptapState.simple_content.length().to(str),
                    "0",
                ),
                size="sm",
                c="gray",
                mt="sm",
            ),
            # Minimal toolbar example
            mn.title("Minimal Toolbar", order=2, mt="xl"),
            mn.text(
                "Custom toolbar with only basic formatting controls.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.minimal_toolbar_content,
                on_update=TiptapState.update_minimal_toolbar_content,
                placeholder="Type with minimal toolbar...",
                toolbar_config=mn.EditorToolbarConfig(
                    control_groups=[
                        mn.ToolbarControlGroup.BASIC_FORMATTING.value,
                        mn.ToolbarControlGroup.HISTORY.value,
                    ]
                ),
                width="100%",
            ),
            # Custom toolbar example
            mn.title("Custom Toolbar Groups", order=2, mt="xl"),
            mn.text(
                "Fully custom toolbar configuration with specific controls.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.custom_toolbar_content,
                on_update=TiptapState.update_custom_toolbar_content,
                placeholder="Custom toolbar example...",
                toolbar_config=mn.EditorToolbarConfig(
                    control_groups=[
                        ["bold", "italic", "underline"],
                        ["h1", "h2", "h3"],
                        ["bulletList", "orderedList"],
                        ["link", "unlink"],
                        ["image"],
                    ]
                ),
                width="100%",
            ),
            # Controlled editor with custom toolbar
            mn.title("Controlled Editor with State", order=2, mt="xl"),
            mn.text(
                "Editor content synced with Reflex state via on_update callback.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.controlled_content,
                on_update=TiptapState.update_controlled_content,
                placeholder="Start typing...",
                width="100%",
            ),
            # Color picker example
            mn.title("Text Color Support", order=2, mt="xl"),
            mn.text(
                "Select text and apply colors using the color picker or preset colors.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.color_content,
                on_update=TiptapState.update_color_content,
                placeholder="Select text and change its color...",
                toolbar_config=mn.EditorToolbarConfig(
                    control_groups=[
                        mn.ToolbarControlGroup.BASIC_FORMATTING.value,
                        mn.ToolbarControlGroup.COLORS.value,
                        mn.ToolbarControlGroup.HISTORY.value,
                    ]
                ),
                width="100%",
            ),
            # Minimal editor (no toolbar)
            mn.title("Content Area", order=2, mt="xl"),
            mn.text(
                "The editor automatically includes a full toolbar with all controls.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.minimal_content,
                on_update=TiptapState.update_minimal_content,
                placeholder="Try Cmd+B for bold, Cmd+I for italic...",
                width="100%",
            ),
            # Code and special formatting
            mn.title("Code Support", order=2, mt="xl"),
            mn.text(
                "Inline code and code blocks with syntax highlighting.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.code_content,
                placeholder="Write some code...",
                width="100%",
            ),
            # Readonly editor
            mn.title("Read-Only Editor", order=2, mt="xl"),
            mn.text(
                "Content display mode - no editing allowed.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content=TiptapState.readonly_content,
                editable=False,
                width="100%",
            ),
            # Text alignment example
            mn.title("Text Alignment", order=2, mt="xl"),
            mn.text(
                "Align paragraphs left, center, right, or justify.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content="""<h2 style="text-align: left;">Left Aligned Heading</h2>
<p style="text-align: left;">This paragraph is aligned to the left.</p>
<h2 style="text-align: center;">Center Aligned Heading</h2>
<p style="text-align: center;">This paragraph is centered.</p>
<h2 style="text-align: right;">Right Aligned Heading</h2>
<p style="text-align: right;">This paragraph is aligned to the right.</p>""",
                width="100%",
            ),
            # Subscript and superscript
            mn.title("Subscript & Superscript", order=2, mt="xl"),
            mn.text(
                "Useful for mathematical formulas and footnotes.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content="""<p>Chemical formula: H<sub>2</sub>O</p>
<p>Mathematical expression: E = mc<sup>2</sup></p>
<p>Footnote reference<sup>1</sup></p>""",
                width="100%",
            ),
            # Variant example - subtle
            mn.title("Subtle Variant", order=2, mt="xl"),
            mn.text(
                "Borderless design with larger controls and reduced spacing.",
                size="md",
                c="gray",
                mb="md",
            ),
            mn.rich_text_editor(
                content="<p>This editor uses the subtle variant style.</p>",
                variant="subtle",
                width="100%",
            ),
            # Action buttons
            rx.hstack(
                rx.button(
                    "Reset All Content",
                    on_click=TiptapState.reset_content,
                    c="red",
                    variant="outline",
                ),
                mt="lg",
                mb="lg",
            ),
            # Usage notes
            mn.title("Usage Notes", order=2, mt="lg"),
            mn.list_(
                mn.list_.item(
                    "Use ",
                    mn.code("mn.rich_text_editor()"),
                    " - all-in-one component with full toolbar",
                ),
                mn.list_.item(
                    "Handles Tiptap editor lifecycle automatically via inline wrapper",
                ),
                mn.list_.item(
                    "Content is HTML - use ",
                    mn.code("on_update"),
                    " event to sync with state",
                ),
                mn.list_.item(
                    "Set ",
                    mn.code("editable=False"),
                    " for read-only display mode",
                ),
                mn.list_.item(
                    "All extensions included: Highlight, TextAlign, Color, "
                    "Link, Subscript, Superscript, Code, and more",
                ),
                mn.list_.item(
                    "Keyboard shortcuts work automatically (Cmd+B, Cmd+I, etc.)",
                ),
                type="unordered",
                size="lg",
                spacing="md",
            ),
            # Technical details
            mn.title("Technical Details", order=2, mt="lg"),
            mn.text(
                "Pure Python implementation - no external JavaScript files needed.",
                size="md",
            ),
            mn.list_(
                mn.list_.item(
                    "Wrapper component defined inline via ",
                    mn.code("_get_custom_code()"),
                ),
                mn.list_.item(
                    "Handles ",
                    mn.code("useEditor"),
                    " React hook internally with ",
                    mn.code("React.createElement"),
                ),
                mn.list_.item(
                    "Syncs content bidirectionally between Reflex state "
                    "and Tiptap editor",
                ),
                mn.list_.item(
                    "Based on Tiptap 2.x with Mantine UI components",
                ),
                type="unordered",
                size="lg",
                spacing="md",
            ),
            width="100%",
            padding="md",
            mb="6rem",
        ),
        size="md",
        w="100%",
    )

"""Reflex wrapper for @uiw/react-markdown-preview.

Provides GitHub-flavored markdown rendering with optional Mermaid diagrams,
KaTeX math support, configurable security presets, and automatic dark mode
integration through a custom JavaScript wrapper.

Documentation: https://github.com/uiwjs/react-markdown-preview
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

import reflex as rx
from reflex.assets import asset
from reflex.components.component import ImportVar, NoSSRComponent
from reflex.vars.base import Var

from appkit_mantine.base import MemoizedMantineProvider

MARKDOWN_PREVIEW_VERSION: str = "^5.1.5"
REHYPE_SANITIZE_VERSION: str = "^6.0.0"
REHYPE_REWRITE_VERSION: str = "^4.0.0"
MERMAID_VERSION: str = "^11.0.0"
KATEX_VERSION: str = "^0.16.0"


class MarkdownPreview(NoSSRComponent):
    """Client-side markdown renderer with optional diagram and math support.

    This component wraps `@uiw/react-markdown-preview` and enhances it with a
    custom JavaScript wrapper that adds:
    - Mermaid diagram rendering when ``enable_mermaid`` is true.
    - KaTeX math rendering when ``enable_katex`` is true.
    - Configurable security presets (strict, standard, none) to control HTML
      sanitization and raw HTML rendering.
    - Automatic dark mode integration by reading Reflex color mode settings.

    Example:
        ```python
        import reflex as rx
        import appkit_mantine as mn


        class DocsState(rx.State):
            content: str = "# Markdown Preview\n\nRender diagrams and math."
            render_enhanced: bool = False


        def page() -> rx.Component:
            return mn.markdown_preview(
                source=DocsState.content,
                enable_mermaid=DocsState.render_enhanced,
                enable_katex=DocsState.render_enhanced,
                security_level="standard",
                style={"padding": "16px"},
            )
        ```

        Toggle ``DocsState.render_enhanced`` to ``True`` once streaming is complete
        to transform Mermaid and KaTeX blocks.
    """

    tag = "MarkdownPreviewWrapper"
    library = (
        None  # "$/public/" + asset(path="markdown_preview_wrapper.js", shared=True)
    )
    is_default = True

    _base_dependencies: ClassVar[list[str]] = [
        f"@uiw/react-markdown-preview@{MARKDOWN_PREVIEW_VERSION}",
        f"rehype-sanitize@{REHYPE_SANITIZE_VERSION}",
        f"rehype-rewrite@{REHYPE_REWRITE_VERSION}",
    ]

    lib_dependencies: list[str] = _base_dependencies.copy()

    # Core content
    source: Var[str | None] = None
    """Markdown source string to render."""

    security_level: Var[Literal["strict", "standard", "none"]] = "standard"
    """Security preset controlling HTML sanitization."""

    # Feature toggles
    enable_mermaid: Var[bool] = False
    """Render Mermaid diagrams when true, otherwise show source fences."""

    enable_katex: Var[bool] = False
    """Render KaTeX math when true, otherwise show source text."""

    class_name: Var[str | None] = None
    """Custom CSS class applied to the wrapper element."""

    prefix_cls: Var[str | None] = "wmde-markdown"
    """Overrides the default CSS class prefix used by the component."""

    disable_copy: Var[bool | None] = None
    """Disable copy button for code blocks when true."""

    remark_plugins: Var[list[Any] | None] = None
    """Additional remark plugins applied before rendering."""

    rehype_plugins: Var[list[Any] | None] = None
    """Additional rehype plugins applied after markdown processing."""

    rehype_rewrite: Var[Any] = None
    """Custom rehype rewrite handler for DOM manipulation."""

    components: Var[dict[str, Any] | None] = None
    """Override React component mappings (advanced usage)."""

    wrapper_element: Var[dict[str, Any] | None] = None
    """Props applied to the wrapper element surrounding the preview."""

    def _get_custom_code(self) -> str:
        """Ensure required CSS bundles are available for the renderer."""
        return """import '@mantine/core/styles.css';
    import '@uiw/react-markdown-preview/markdown.css';"""

    def _should_include_optional_dependency(self, value: Var[Any] | Any) -> bool:
        """Determine whether optional libraries should be bundled."""
        _ = value
        # Always include optional dependencies so rendering can be toggled at runtime.
        return True

    def _get_dependencies_imports(self) -> dict[str, list[ImportVar]]:
        """Include optional dependencies when corresponding features are enabled."""
        dependencies = super()._get_dependencies_imports()

        if self._should_include_optional_dependency(self.enable_mermaid):
            dependencies.setdefault(
                f"mermaid@{MERMAID_VERSION}", [ImportVar(tag=None, render=False)]
            )

        if self._should_include_optional_dependency(self.enable_katex):
            dependencies.setdefault(
                f"katex@{KATEX_VERSION}", [ImportVar(tag=None, render=False)]
            )

        return dependencies

    def _get_dynamic_imports(self) -> str:
        """Get the dynamic import for the custom wrapper component.

        Returns:
            The dynamic import code for the markdown preview wrapper.
        """
        # Get the asset path for the wrapper
        wrapper_path = asset(path="markdown_preview_wrapper.js", shared=True)
        # Format as module import path
        import_path = f"$/public/{wrapper_path}"

        # Return the dynamic import with ClientSide wrapper and lazy loading
        return f"""const {self.tag} = ClientSide(lazy(() =>
    import('{import_path}').then((mod) => ({{ default: mod.MarkdownPreviewWrapper }}))
))"""

    def add_imports(self) -> dict[str, list[str]]:
        """Add necessary imports for lazy loading.

        Returns:
            The imports needed for ClientSide and lazy.
        """
        return {
            "react": ["lazy"],
            f"$/{rx.constants.Dirs.UTILS}/context": ["ClientSide"],
        }

    @staticmethod
    def _get_app_wrap_components() -> dict[tuple[int, str], rx.Component]:
        """Ensure the Mantine provider wraps applications using this component."""
        return {
            (44, "MantineProvider"): MemoizedMantineProvider.create(),
        }


markdown_preview = MarkdownPreview.create

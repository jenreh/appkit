"""Mantine Textarea component wrapper for Reflex.

Provides a multiline text input with autosize support.

⚠️ CONTROLLED VS UNCONTROLLED TEXTAREAS:

Unlike rx.input() which has built-in debouncing, Mantine's Textarea does NOT
have automatic debouncing. This means:

PROBLEM WITH CONTROLLED INPUTS (value + on_change):
  When you bind value + on_change to state, every keystroke triggers:
  1. A state update sent to the backend
  2. A re-render of the component
  3. The cursor moves to the end of the input

  This is a fundamental React constraint, not a Reflex/Mantine bug.

RECOMMENDED PATTERNS:

1. **Uncontrolled with on_blur** (BEST for production) ✅
   ```python
   mn.textarea(
       default_value=State.text,
       on_blur=State.set_text,
   )
   ```
   Pros: No cursor jumping, better performance, simpler
   Cons: Updates only on blur

2. **Hybrid: default_value + on_change** (LIVE UPDATES WITH NO CURSOR JUMP) ✅
   ```python
   mn.textarea(
       default_value=State.text,
       on_change=State.update_counts,
   )
   ```
   This is the KEY to live character counting WITHOUT cursor jumping!

   How it works:
   - default_value keeps textarea uncontrolled (preserves cursor position)
   - on_change still fires on every keystroke
   - State updates are for UI display only (character/word count)
   - React doesn't re-render the textarea value, so cursor stays in place

   Perfect for: Character counts, live validation feedback, progress indicators

3. **Custom debounced textarea** (complex, rarely needed)
   Implement frontend debouncing with JavaScript refs to preserve cursor
   position while updating state in real-time.

See `textarea_examples.py` for complete working examples including the
hybrid approach that solves cursor jumping while enabling live updates!

See `mantine_textarea()` function for detailed usage and examples.
"""

from __future__ import annotations

from typing import Literal

from reflex.vars.base import Var

from appkit_mantine.base import (
    MantineInputComponentBase,
)


class Textarea(MantineInputComponentBase):
    """Mantine Textarea component with autosize support.

    Based on: https://mantine.dev/core/textarea/

    Inherits common input props from MantineInputComponentBase.

    ⚠️ CURSOR JUMPING WITH CONTROLLED INPUTS:
    When using value + on_change (controlled input), the cursor will jump to the
    end while typing because:
    - Every keystroke updates the state
    - Every state update causes a re-render
    - React resets the cursor position to the end

    SOLUTION: Use default_value + on_blur instead for production code.
    This is documented in the module docstring above.

    See `mantine_textarea()` function for detailed documentation and examples.
    """

    tag = "Textarea"

    # HTML textarea attributes
    rows: Var[int] = None
    """Number of visible text lines (when not using autosize)."""

    cols: Var[int] = None
    """Visible width in characters."""

    wrap: Var[Literal["soft", "hard", "off"]] = None
    """Text wrapping behavior: soft (default), hard, or off."""

    # Autosize feature (uses react-textarea-autosize)
    autosize: Var[bool] = None
    """Enable automatic height adjustment based on content."""

    min_rows: Var[int] = None
    """Minimum number of rows when using autosize."""

    max_rows: Var[int] = None
    """Maximum number of rows when using autosize."""

    # Resize control
    resize: Var[Literal["none", "vertical", "both", "horizontal"]] = None
    """CSS resize property to control manual resizing."""

    # Mantine styles prop for targeting internal sub-components
    styles: Var[dict] = None
    """Mantine styles object for targeting internal elements (root, wrapper, input)."""


# ============================================================================
# Convenience Function
# ============================================================================


textarea = Textarea.create

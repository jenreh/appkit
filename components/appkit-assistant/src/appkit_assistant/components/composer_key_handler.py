import reflex as rx


class KeyboardShortcuts(rx.Component):
    """Keyboard shortcut handler component for the composer.

    Handles:
    - Enter without Shift: Submit form (unless command palette is open)
    - ArrowUp/ArrowDown: Navigate command palette
    - Tab: Move to next command in palette
    - Escape: Dismiss command palette
    - Enter when palette open: Select current command
    """

    library = None  # No external library needed
    tag = None

    def add_imports(self) -> dict:
        return {
            "react": [rx.ImportVar(tag="useEffect")],
        }

    def add_hooks(self) -> list[str]:
        return [
            """
useEffect(() => {
    // Helper to scroll selected item into view after DOM update
    const scrollSelectedIntoView = () => {
        // Try multiple times with increasing delays to catch the DOM update
        const attempts = [50, 100, 200];
        attempts.forEach(delay => {
            setTimeout(() => {
                const palette = document.getElementById('command-palette');
                if (!palette) return;

                // Find the selected item by data-selected attribute
                const selected = palette.querySelector('[data-selected="true"]');
                if (selected) {
                    selected.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                }
            }, delay);
        });
    };

    const handleKeydown = (e) => {
        const textarea = document.getElementById('composer-area');
        const submitBtn = document.getElementById('composer-submit');

        // Only handle if we're focused on the textarea
        if (document.activeElement !== textarea) return;
        if (!submitBtn) return;

        // Check if command palette is open by looking for the palette element
        // Use getBoundingClientRect to check actual visibility (works with
        // absolute positioned elements)
        const paletteEl = document.getElementById('command-palette');
        const paletteOpen = paletteEl !== null
                            && paletteEl.getBoundingClientRect().height > 0;

        // Command palette navigation when open
        if (paletteOpen) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                const btn = document.getElementById('cmd-palette-up');
                if (btn) {
                    btn.click();
                    scrollSelectedIntoView();
                }
                return;
            }
            if (e.key === 'ArrowDown' || e.key === 'Tab') {
                e.preventDefault();
                const btn = document.getElementById('cmd-palette-down');
                if (btn) {
                    btn.click();
                    scrollSelectedIntoView();
                }
                return;
            }
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const btn = document.getElementById('cmd-palette-select');
                if (btn) btn.click();
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                const btn = document.getElementById('cmd-palette-dismiss');
                if (btn) btn.click();
                return;
            }
        }

        // Default Enter behavior (submit) when palette is closed
        if (e.key === 'Enter' && !e.shiftKey && !paletteOpen) {
            e.preventDefault();
            if (textarea.value.trim() && !submitBtn.disabled) {
                submitBtn.click();
            }
        }
    };

    // Use document-level listener to ensure we catch events even if useEffect
    // runs before textarea is mounted
    document.addEventListener('keydown', handleKeydown);
    return () => document.removeEventListener('keydown', handleKeydown);
}, []);
            """
        ]


# Create an instance function
keyboard_shortcuts = KeyboardShortcuts.create

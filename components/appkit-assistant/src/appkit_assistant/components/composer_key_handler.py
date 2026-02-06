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
    const textarea = document.getElementById('composer-area');
    const submitBtn = document.getElementById('composer-submit');

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

    if (textarea && submitBtn) {
        const handleKeydown = (e) => {
            // Check if command palette is open by looking for the palette element
            const paletteEl = document.getElementById('command-palette');
            const paletteOpen = paletteEl !== null;

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
        textarea.addEventListener('keydown', handleKeydown);
        return () => textarea.removeEventListener('keydown', handleKeydown);
    }
}, []);
            """
        ]


# Create an instance function
keyboard_shortcuts = KeyboardShortcuts.create

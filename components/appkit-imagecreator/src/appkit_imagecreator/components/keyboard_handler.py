import reflex as rx


class KeyboardShortcuts(rx.Component):
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
    const findTextarea = () => {
        let el = document.getElementById('image-prompt-area');
        if (el && el.tagName !== 'TEXTAREA') {
            el = el.querySelector('textarea');
        }
        return el;
    };

    const textarea = findTextarea();

    if (textarea) {
        const handleKeydown = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const submitBtn = document.getElementById('prompt-submit');
                if (textarea.value.trim() && submitBtn && !submitBtn.disabled) {
                    textarea.blur();
                    submitBtn.click();
                    textarea.focus();
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

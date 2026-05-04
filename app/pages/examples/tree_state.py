import reflex as rx


class TreeExampleState(rx.State):
    search: str = ""
    checked: list[str] = []

    def set_search(self, search: str) -> None:
        self.search = search

    def set_checked(self, checked: list[str]) -> None:
        self.checked = checked

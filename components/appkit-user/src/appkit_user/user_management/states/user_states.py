from collections.abc import AsyncGenerator
from typing import Any

import reflex as rx

from appkit_commons.database.session import get_asyncdb_session
from appkit_commons.roles import Role
from appkit_user.authentication.backend.database.user_repository import user_repo
from appkit_user.authentication.backend.models import User, UserCreate
from appkit_user.authentication.decorators import is_authenticated


class UserState(rx.State):
    users: list[User] = []
    selected_user: User | None = None
    is_loading: bool = False
    available_roles: list[dict[str, str]] = []
    grouped_roles: dict[str, list[dict[str, str]]] = {}
    sorted_group_names: list[str] = []

    add_modal_open: bool = False
    edit_modal_open: bool = False
    search_filter: str = ""

    def set_search_filter(self, value: str) -> None:
        """Update the search filter."""
        self.search_filter = value

    @rx.var
    def filtered_users(self) -> list[User]:
        """Return users filtered by search text."""
        if not self.search_filter:
            return self.users
        search = self.search_filter.lower()
        return [
            u
            for u in self.users
            if search in u.name.lower() or search in u.email.lower()
        ]

    def open_add_modal(self) -> None:
        """Open the add user modal."""
        self.add_modal_open = True

    def close_add_modal(self) -> None:
        """Close the add user modal."""
        self.add_modal_open = False

    def open_edit_modal(self) -> None:
        """Open the edit user modal."""
        self.edit_modal_open = True

    def close_edit_modal(self) -> None:
        """Close the edit user modal."""
        self.edit_modal_open = False
        self.selected_user = None

    async def select_user_and_open_edit(self, user_id: int) -> None:
        """Select a user and open the edit modal."""
        await self.select_user(user_id)
        self.open_edit_modal()

    def set_available_roles(self, roles_list: list[Role]) -> None:
        """Set roles grouped by group in original order."""
        # Normalize roles to dict structure
        roles_dicts = [
            role
            if isinstance(role, dict)
            else {
                "name": role.name,
                "label": role.label,
                "description": role.description,
                "group": role.group or "default",
            }
            for role in roles_list
        ]

        # Group roles by group (preserving order)
        grouped = {}
        group_order = []
        for role in roles_dicts:
            group_name = role.get("group", "default")
            if group_name not in grouped:
                grouped[group_name] = []
                group_order.append(group_name)
            grouped[group_name].append(role)

        self.available_roles = roles_dicts
        self.grouped_roles = grouped
        self.sorted_group_names = group_order

    def _get_selected_roles(self, form_data: dict) -> list[str]:
        """Extract selected roles from form data."""
        return [
            key.split("role_")[1]
            for key, value in form_data.items()
            if key.startswith("role_") and value == "on"
        ]

    async def _load_users(self, limit: int = 200, offset: int = 0) -> None:
        """Internal load logic."""
        async with get_asyncdb_session() as session:
            user_entities = await user_repo.find_all_paginated(
                session, limit=limit, offset=offset
            )
            self.users = [User(**user.to_dict()) for user in user_entities]

    @is_authenticated
    async def load_users(
        self, limit: int = 200, offset: int = 0
    ) -> AsyncGenerator[Any, None]:
        self.is_loading = True
        yield
        try:
            await self._load_users(limit, offset)
        finally:
            self.is_loading = False

    @is_authenticated
    async def create_user(self, form_data: dict) -> AsyncGenerator[Any, None]:
        self.is_loading = True
        yield
        try:
            roles = self._get_selected_roles(form_data)
            new_user = UserCreate(
                name=form_data["name"],
                email=form_data["email"],
                password=form_data["password"],
                is_verified=True,
                needs_password_reset=True,
                roles=roles,
            )

            async with get_asyncdb_session() as session:
                await user_repo.create_new_user(session, new_user)

            await self._load_users()
            self.close_add_modal()
            self.is_loading = False
            yield rx.toast.info(
                f"Benutzer {form_data['email']} angelegt.",
                position="top-right",
            )
        except Exception as e:
            self.is_loading = False
            yield rx.toast.error(f"Fehler: {e}", position="top-right")

    @is_authenticated
    async def update_user(self, form_data: dict) -> AsyncGenerator[Any, None]:
        self.is_loading = True
        yield
        try:
            if not self.selected_user:
                self.is_loading = False
                yield rx.toast.error("Kein Benutzer ausgewählt.", position="top-right")
                return

            # Handle boolean fields (checkboxes)
            for field in ["is_active", "is_admin", "is_verified"]:
                form_data[field] = bool(form_data.get(field))

            form_data["roles"] = self._get_selected_roles(form_data)

            # Create update object and set ID
            user = UserCreate(**form_data)
            user.user_id = self.selected_user.user_id

            async with get_asyncdb_session() as session:
                await user_repo.update_from_model(session, user)

            await self._load_users()
            self.close_edit_modal()
            self.is_loading = False
            yield rx.toast.info(
                f"Benutzer {form_data['email']} wurde aktualisiert.",
                position="top-right",
            )
        except Exception as e:
            self.is_loading = False
            yield rx.toast.error(f"Fehler: {e}", position="top-right")

    @is_authenticated
    async def delete_user(self, user_id: int) -> AsyncGenerator[Any, None]:
        self.is_loading = True
        yield
        try:
            async with get_asyncdb_session() as session:
                user_entity = await user_repo.find_by_id(session, user_id)
                if not user_entity:
                    self.is_loading = False
                    yield rx.toast.error(
                        "Benutzer kann nicht gelöscht werden, er wurde nicht gefunden.",
                        position="top-right",
                    )
                    return

                deleted = await user_repo.delete_by_id(session, user_id)
                if not deleted:
                    self.is_loading = False
                    yield rx.toast.error(
                        "Benutzer konnte nicht gelöscht werden.",
                        position="top-right",
                    )
                    return

            await self._load_users()
            self.is_loading = False
            yield rx.toast.info("Benutzer wurde gelöscht.", position="top-right")
        except Exception as e:
            self.is_loading = False
            yield rx.toast.error(f"Fehler: {e}", position="top-right")

    async def select_user(self, user_id: int) -> None:
        async with get_asyncdb_session() as session:
            user_entity = await user_repo.find_by_id(session, user_id)
            self.selected_user = User(**user_entity.to_dict()) if user_entity else None

    async def user_has_role(self, role_name: str) -> bool:
        """Check if the selected user has a specific role."""
        if not self.selected_user:
            return False
        return role_name in self.selected_user.roles

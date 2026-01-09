import reflex as rx
from reflex.components.sonner.toast import Toaster

from appkit_commons.database.session import get_asyncdb_session
from appkit_user.authentication.backend.models import Role, User, UserCreate
from appkit_user.authentication.backend.user_repository import user_repo


class UserState(rx.State):
    users: list[User] = []
    selected_user: User | None
    is_loading: bool = False
    available_roles: list[dict[str, str]] = []

    def set_available_roles(self, roles_list: list[Role]) -> None:
        """Set the available roles."""
        self.available_roles = roles_list

    def _get_selected_roles(self, form_data: dict) -> list[str]:
        roles = []
        for key, value in form_data.items():
            if key.startswith("role_") and value == "on":
                roles.append(key.split("role_")[1])
        return roles

    async def load_users(self, limit: int = 200, offset: int = 0) -> None:
        self.is_loading = True
        async with get_asyncdb_session() as session:
            user_entities = await user_repo.find_all_paginated(
                session, limit=limit, offset=offset
            )
            self.users = [User(**user.to_dict()) for user in user_entities]
        self.is_loading = False

    async def create_user(self, form_data: dict) -> Toaster:
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

        await self.load_users()

        return rx.toast.info(
            f"Benutzer {form_data['email']} angelegt.", position="top-right"
        )

    async def update_user(self, form_data: dict) -> Toaster:
        if not self.selected_user:
            return rx.toast.error(
                "Kein Benutzer ausgewählt.",
                position="top-right",
            )

        if form_data.get("is_active"):
            form_data["is_active"] = True
        else:
            form_data["is_active"] = False

        if form_data.get("is_admin"):
            form_data["is_admin"] = True
        else:
            form_data["is_admin"] = False

        if form_data.get("is_verified"):
            form_data["is_verified"] = True
        else:
            form_data["is_verified"] = False

        form_data["roles"] = self._get_selected_roles(form_data)

        user = UserCreate(**form_data)
        user.user_id = self.selected_user.user_id

        async with get_asyncdb_session() as session:
            await user_repo.update_from_model(session, user)

        await self.load_users()

        return rx.toast.info(
            f"Benutzer {form_data['email']} wurde aktualisiert.",
            position="top-right",
        )

    async def delete_user(self, user_id: int) -> Toaster:
        async with get_asyncdb_session() as session:
            user_entity = await user_repo.find_by_id(session, user_id)
            if not user_entity:
                return rx.toast.error(
                    "Benutzer kann nicht gelöscht werden, er wurde nicht gefunden.",
                    position="top-right",
                )

            deleted = await user_repo.delete_by_id(session, user_id)
            if not deleted:
                return rx.toast.error(
                    "Benutzer konnte nicht gelöscht werden.",
                    position="top-right",
                )

        await self.load_users()
        return rx.toast.info("Benutzer wurde gelöscht.", position="top-right")

    async def select_user(self, user_id: int) -> None:
        async with get_asyncdb_session() as session:
            user_entity = await user_repo.find_by_id(session, user_id)
            self.selected_user = User(**user_entity.to_dict()) if user_entity else None

    async def user_has_role(self, role_name: str) -> bool:
        """Check if the selected user has a specific role."""
        if not self.selected_user:
            return False
        return role_name in self.selected_user.roles

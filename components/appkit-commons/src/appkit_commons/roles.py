from pydantic import BaseModel


class Role(BaseModel):
    id: int | None = None
    name: str
    label: str
    description: str | None = ""
    group: str = "default"


NO_ROLE = Role(
    name="__none__",
    label="Keine Einschränkung",
    description="Kein Rollenzwang",
    group="default",
)

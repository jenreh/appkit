from pydantic import BaseModel


class Role(BaseModel):
    id: int | None = None
    name: str
    label: str
    description: str | None = ""
    group: str = "default"

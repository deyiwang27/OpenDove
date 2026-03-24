from dataclasses import dataclass

from opendove.models.task import Role


@dataclass(frozen=True)
class RoleDefinition:
    role: Role
    responsibility: str
    output: str


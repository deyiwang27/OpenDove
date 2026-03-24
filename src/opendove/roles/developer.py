from opendove.models.task import Role
from opendove.roles.base import RoleDefinition


DEVELOPER = RoleDefinition(
    role=Role.DEVELOPER,
    responsibility="Implement the task and provide test evidence.",
    output="Code, tests, and execution artifacts.",
)


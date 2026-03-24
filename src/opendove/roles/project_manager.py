from opendove.models.task import Role
from opendove.roles.base import RoleDefinition


PROJECT_MANAGER = RoleDefinition(
    role=Role.PROJECT_MANAGER,
    responsibility="Assign tasks, control retries, and trigger escalation when needed.",
    output="An execution plan with ownership and limits.",
)


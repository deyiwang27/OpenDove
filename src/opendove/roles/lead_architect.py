from opendove.models.task import Role
from opendove.roles.base import RoleDefinition


LEAD_ARCHITECT = RoleDefinition(
    role=Role.LEAD_ARCHITECT,
    responsibility="Define the implementation approach and verify integration behavior.",
    output="A technical plan and integration review.",
)


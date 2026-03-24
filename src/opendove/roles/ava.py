from opendove.models.task import Role
from opendove.roles.base import RoleDefinition


AVA = RoleDefinition(
    role=Role.AVA,
    responsibility="Approve, reject, or escalate based on the task contract and evidence.",
    output="A blocking validation decision.",
)


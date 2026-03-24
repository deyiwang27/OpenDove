from opendove.models.task import Role
from opendove.roles.base import RoleDefinition


PRODUCT_MANAGER = RoleDefinition(
    role=Role.PRODUCT_MANAGER,
    responsibility="Define the task scope, intent, and success criteria.",
    output="A task contract that can be validated later.",
)


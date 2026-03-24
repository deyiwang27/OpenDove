from opendove.models.task import Role


def build_orchestration_summary() -> str:
    ordered_roles = [
        Role.PRODUCT_MANAGER,
        Role.PROJECT_MANAGER,
        Role.LEAD_ARCHITECT,
        Role.DEVELOPER,
        Role.AVA,
    ]
    path = " -> ".join(role.value for role in ordered_roles)
    return f"OpenDove orchestration path: {path}"


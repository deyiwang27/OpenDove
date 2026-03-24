"""add task dag fields

Revision ID: a1b2c3d4e5f6
Revises: 9b2c9da2df1c
Create Date: 2026-03-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9b2c9da2df1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "tasks",
        sa.Column("depends_on", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "tasks",
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default=sa.text("'low'")),
    )
    op.add_column("tasks", sa.Column("parent_issue_number", sa.Integer(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("github_pr_url", sa.Text(), nullable=False, server_default=sa.text("''")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tasks", "github_pr_url")
    op.drop_column("tasks", "parent_issue_number")
    op.drop_column("tasks", "risk_level")
    op.drop_column("tasks", "depends_on")

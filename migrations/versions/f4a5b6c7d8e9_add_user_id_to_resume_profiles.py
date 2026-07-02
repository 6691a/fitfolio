"""add user_id to resume_profiles

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("resume_profiles", sa.Column("user_id", sa.Integer(), nullable=False))
    op.create_index(op.f("ix_resume_profiles_user_id"), "resume_profiles", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_resume_profiles_user_id_users"),
        "resume_profiles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("fk_resume_profiles_user_id_users"), "resume_profiles", type_="foreignkey")
    op.drop_index(op.f("ix_resume_profiles_user_id"), table_name="resume_profiles")
    op.drop_column("resume_profiles", "user_id")

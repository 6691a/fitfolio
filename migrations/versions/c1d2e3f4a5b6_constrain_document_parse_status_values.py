"""constrain document parse status values

Revision ID: c1d2e3f4a5b6
Revises: b6c2a4f8d901
Create Date: 2026-06-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b6c2a4f8d901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATUS_VALUES = "'pending', 'started', 'retry', 'done', 'failed'"
_CONSTRAINT_NAME = "ck_documents_status_parse_status"


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("documents", "status", existing_type=sa.String(length=20), server_default="pending")
    op.create_check_constraint(
        _CONSTRAINT_NAME,
        "documents",
        f"status IN ({_STATUS_VALUES})",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(_CONSTRAINT_NAME, "documents", type_="check")
    op.alter_column("documents", "status", existing_type=sa.String(length=20), server_default=None)

"""split resume raw_text into document_text and image_text

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-06-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "resume_profiles",
        sa.Column("document_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "resume_profiles",
        sa.Column("image_text", sa.Text(), nullable=False, server_default=""),
    )
    op.execute("UPDATE resume_profiles SET document_text = raw_text")
    op.alter_column("resume_profiles", "document_text", server_default=None)
    op.drop_column("resume_profiles", "raw_text")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "resume_profiles",
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
    )
    op.execute("UPDATE resume_profiles SET raw_text = TRIM(BOTH E'\\n' FROM document_text || E'\\n\\n' || image_text)")
    op.alter_column("resume_profiles", "raw_text", server_default=None)
    op.drop_column("resume_profiles", "image_text")
    op.drop_column("resume_profiles", "document_text")

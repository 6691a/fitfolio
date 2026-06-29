"""add reusable url document unique index

Revision ID: f8a9b0c1d2e3
Revises: e2f3a4b5c6d7
Create Date: 2026-06-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "ux_documents_reusable_url"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        f"""
        CREATE UNIQUE INDEX {_INDEX_NAME}
        ON documents (document_type, format, source_url)
        WHERE
            source_url IS NOT NULL
            AND format = 'url'
            AND status IN ('pending', 'started', 'retry', 'done')
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP INDEX IF EXISTS {_INDEX_NAME}")

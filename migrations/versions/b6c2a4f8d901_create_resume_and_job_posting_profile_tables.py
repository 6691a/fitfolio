"""create resume and job posting profile tables

Revision ID: b6c2a4f8d901
Revises: f3a91c2b7e44
Create Date: 2026-06-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c2a4f8d901"
down_revision: Union[str, Sequence[str], None] = "f3a91c2b7e44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "resume_profiles",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("self_introduction", sa.Text(), nullable=True),
        sa.Column("career_summary", sa.Text(), nullable=True),
        sa.Column("work_experiences", sa.JSON(), nullable=False),
        sa.Column("projects", sa.JSON(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("education", sa.JSON(), nullable=False),
        sa.Column("certifications", sa.JSON(), nullable=False),
        sa.Column("raw_sections", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index(op.f("ix_resume_profiles_document_id"), "resume_profiles", ["document_id"], unique=False)
    op.create_index(op.f("ix_resume_profiles_id"), "resume_profiles", ["id"], unique=False)

    op.create_table(
        "job_posting_profiles",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("career_requirement", sa.String(length=255), nullable=True),
        sa.Column("education_requirement", sa.String(length=255), nullable=True),
        sa.Column("opening_period", sa.String(length=255), nullable=True),
        sa.Column("deadline", sa.String(length=100), nullable=True),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("qualifications", sa.JSON(), nullable=False),
        sa.Column("preferred_qualifications", sa.JSON(), nullable=False),
        sa.Column("benefits", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("raw_sections", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index(op.f("ix_job_posting_profiles_document_id"), "job_posting_profiles", ["document_id"], unique=False)
    op.create_index(op.f("ix_job_posting_profiles_id"), "job_posting_profiles", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_job_posting_profiles_id"), table_name="job_posting_profiles")
    op.drop_index(op.f("ix_job_posting_profiles_document_id"), table_name="job_posting_profiles")
    op.drop_table("job_posting_profiles")
    op.drop_index(op.f("ix_resume_profiles_id"), table_name="resume_profiles")
    op.drop_index(op.f("ix_resume_profiles_document_id"), table_name="resume_profiles")
    op.drop_table("resume_profiles")

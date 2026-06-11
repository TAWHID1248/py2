"""Phase 3 — add attachment fields to campaigns table

Revision ID: 001_phase3
Revises:
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision = "001_phase3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("campaigns") as batch:
        batch.add_column(sa.Column("use_account_rotation", sa.Boolean(), server_default="0"))
        batch.add_column(sa.Column("attach_pdf", sa.Boolean(), server_default="0"))
        batch.add_column(sa.Column("pdf_template_html", sa.Text(), nullable=True))
        batch.add_column(sa.Column("attach_word", sa.Boolean(), server_default="0"))
        batch.add_column(sa.Column("word_template_path", sa.String(500), nullable=True))
        batch.add_column(sa.Column("attachment_name_pattern", sa.String(200), nullable=True))


def downgrade():
    with op.batch_alter_table("campaigns") as batch:
        for col in [
            "use_account_rotation", "attach_pdf", "pdf_template_html",
            "attach_word", "word_template_path", "attachment_name_pattern",
        ]:
            batch.drop_column(col)

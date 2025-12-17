"""add device history table

Revision ID: 20250101_add_device_history
Revises: None
Create Date: 2025-12-17
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250101_add_device_history"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "device_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("device.id", ondelete="SET NULL"), index=True, nullable=True),
        sa.Column("change_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("diff", sa.JSON(), nullable=False),
        sa.Column("summary", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now(), index=True),
    )
    op.create_index(
        "idx_history_device_created_at",
        "device_history",
        ["device_id", "created_at"],
    )


def downgrade():
    op.drop_index("idx_history_device_created_at", table_name="device_history")
    op.drop_table("device_history")


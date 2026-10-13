"""add webhooks

Revision ID: 20261013_add_webhooks
Revises: 20261013_ipam_observations
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa


revision = "20261013_add_webhooks"
down_revision = "20261013_ipam_observations"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "webhook" not in existing:
        op.create_table(
            "webhook",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("url", sa.String(length=2048), nullable=False),
            sa.Column("secret", sa.String(length=255)),
            sa.Column("events", sa.String(length=500), nullable=False, server_default="*"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
    if "webhook_delivery" not in existing:
        op.create_table(
            "webhook_delivery",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("webhook_id", sa.Integer(), sa.ForeignKey("webhook.id", ondelete="CASCADE"), nullable=False),
            sa.Column("delivery_id", sa.String(length=36), nullable=False),
            sa.Column("event", sa.String(length=64), nullable=False),
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status_code", sa.Integer()),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("error", sa.String(length=500)),
            sa.Column("duration_ms", sa.Integer()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_webhook_delivery_webhook_id", "webhook_delivery", ["webhook_id"])
        op.create_index("ix_webhook_delivery_delivery_id", "webhook_delivery", ["delivery_id"])
        op.create_index("ix_webhook_delivery_created_at", "webhook_delivery", ["created_at"])


def downgrade():
    op.drop_table("webhook_delivery")
    op.drop_table("webhook")

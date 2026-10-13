"""add tags and device links

Revision ID: 20261013_add_tags_links
Revises: 20261013_add_subnets
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa


revision = "20261013_add_tags_links"
down_revision = "20261013_add_subnets"
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: a database bootstrapped via create_all() may already have these
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "tag" not in existing:
        op.create_table(
            "tag",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        )
        op.create_index("ix_tag_name", "tag", ["name"], unique=True)

    if "device_tag" not in existing:
        op.create_table(
            "device_tag",
            sa.Column("device_id", sa.Integer(), sa.ForeignKey("device.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
        )
        op.create_index("ix_device_tag_tag_id", "device_tag", ["tag_id"])

    if "device_link" not in existing:
        op.create_table(
            "device_link",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_id", sa.Integer(), sa.ForeignKey("device.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_id", sa.Integer(), sa.ForeignKey("device.id", ondelete="CASCADE"), nullable=False),
            sa.Column("link_type", sa.String(length=20), nullable=False),
            sa.Column("port", sa.String(length=50)),
            sa.Column("notes", sa.String(length=255)),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
            sa.UniqueConstraint("source_id", "target_id", "link_type", name="uq_device_link"),
            sa.CheckConstraint("source_id != target_id", name="ck_device_link_not_self"),
        )
        op.create_index("ix_device_link_source_id", "device_link", ["source_id"])
        op.create_index("ix_device_link_target_id", "device_link", ["target_id"])
        op.create_index("ix_device_link_link_type", "device_link", ["link_type"])


def downgrade():
    op.drop_table("device_link")
    op.drop_table("device_tag")
    op.drop_table("tag")

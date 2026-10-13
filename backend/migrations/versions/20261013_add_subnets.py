"""add subnet table for IPAM

Revision ID: 20261013_add_subnets
Revises: 20250101_add_device_history
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261013_add_subnets"
down_revision = "20250101_add_device_history"
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent: a database bootstrapped via create_all() may already have it
    inspector = sa.inspect(op.get_bind())
    if "subnet" in inspector.get_table_names():
        return
    op.create_table(
        "subnet",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cidr", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100)),
        sa.Column("description", sa.Text()),
        sa.Column("vlan_id", sa.Integer()),
        sa.Column("gateway", sa.String(length=64)),
        sa.Column("reserved_ranges", sa.Text()),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )
    op.create_index("ix_subnet_cidr", "subnet", ["cidr"], unique=True)
    op.create_index("ix_subnet_location_id", "subnet", ["location_id"])


def downgrade():
    op.drop_index("ix_subnet_location_id", table_name="subnet")
    op.drop_index("ix_subnet_cidr", table_name="subnet")
    op.drop_table("subnet")

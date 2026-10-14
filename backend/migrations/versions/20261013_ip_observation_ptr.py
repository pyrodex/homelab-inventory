"""reverse DNS (PTR) on ip observations

Revision ID: 20261013_ip_observation_ptr
Revises: 20261013_add_webhooks
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa


revision = "20261013_ip_observation_ptr"
down_revision = "20261013_add_webhooks"
branch_labels = None
depends_on = None


def upgrade():
    # Plain ADD COLUMN (no batch mode): see 20261013_ipam_observations for why
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("ip_observation")}
    if "ptr_hostname" not in existing:
        op.add_column("ip_observation", sa.Column("ptr_hostname", sa.String(length=255)))
    if "ptr_checked_at" not in existing:
        op.add_column("ip_observation", sa.Column("ptr_checked_at", sa.DateTime()))


def downgrade():
    with op.batch_alter_table("ip_observation") as batch:
        batch.drop_column("ptr_checked_at")
        batch.drop_column("ptr_hostname")

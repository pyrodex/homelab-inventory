"""ipam scanning and dhcp observations

Revision ID: 20261013_ipam_observations
Revises: 20261013_add_tags_links
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa


revision = "20261013_ipam_observations"
down_revision = "20261013_add_tags_links"
branch_labels = None
depends_on = None

def _subnet_columns():
    # Fresh Column objects each call: a Column can only be attached once
    return [
        sa.Column("scan_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scan_interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_scan_at", sa.DateTime()),
        sa.Column("last_scan_duration_ms", sa.Integer()),
        sa.Column("last_scan_alive", sa.Integer()),
        sa.Column("last_scan_error", sa.String(length=255)),
    ]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("subnet")}
    # Plain ADD COLUMN (no batch mode): batch mode reflects foreign keys, and on
    # a fresh install the referenced core tables don't exist yet at this point.
    for col in _subnet_columns():
        if col.name not in existing_cols:
            op.add_column("subnet", col)

    if "ip_observation" not in inspector.get_table_names():
        op.create_table(
            "ip_observation",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ip", sa.String(length=64), nullable=False),
            sa.Column("hostname", sa.String(length=255)),
            sa.Column("mac", sa.String(length=64)),
            sa.Column("ping_last_checked", sa.DateTime()),
            sa.Column("ping_last_seen", sa.DateTime()),
            sa.Column("ping_reachable", sa.Boolean()),
            sa.Column("ping_rtt_ms", sa.Float()),
            sa.Column("ping_hostname", sa.String(length=255)),
            sa.Column("dhcp_source", sa.String(length=255)),
            sa.Column("dhcp_hostname", sa.String(length=255)),
            sa.Column("dhcp_client_id", sa.String(length=255)),
            sa.Column("dhcp_expires", sa.DateTime()),
            sa.Column("dhcp_active", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("dhcp_last_seen", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_ip_observation_ip", "ip_observation", ["ip"], unique=True)
        op.create_index("ix_ip_observation_ping_last_seen", "ip_observation", ["ping_last_seen"])
        op.create_index("ix_ip_observation_dhcp_source", "ip_observation", ["dhcp_source"])
        op.create_index("ix_ip_observation_dhcp_active", "ip_observation", ["dhcp_active"])


def downgrade():
    op.drop_table("ip_observation")
    with op.batch_alter_table("subnet") as batch:
        for col in reversed(_subnet_columns()):
            batch.drop_column(col.name)

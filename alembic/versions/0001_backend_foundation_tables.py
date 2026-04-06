"""create backend foundation tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_backend_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.String(length=64), primary_key=True),
        sa.Column("auth_subject", sa.String(length=255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("default_role_id", sa.String(length=128), nullable=False),
        sa.Column("entitlement_tier", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "devices",
        sa.Column("device_id", sa.String(length=64), primary_key=True),
        sa.Column("hardware_model", sa.String(length=128), nullable=False),
        sa.Column("firmware_version", sa.String(length=64), nullable=False),
        sa.Column("pairing_code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("device_status", sa.String(length=32), nullable=False),
        sa.Column("bind_status", sa.String(length=32), nullable=False),
        sa.Column("owner_account_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_online_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_devices_owner_account_id", "devices", ["owner_account_id"])
    op.create_index("ix_devices_bind_status", "devices", ["bind_status"])
    op.create_index("ix_devices_last_online_at", "devices", ["last_online_at"])

    op.create_table(
        "device_bindings",
        sa.Column("binding_id", sa.String(length=64), primary_key=True),
        sa.Column("account_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=False),
        sa.Column("device_id", sa.String(length=64), sa.ForeignKey("devices.device_id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unbound_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_device_bindings_account_id", "device_bindings", ["account_id"])
    op.create_index("ix_device_bindings_device_id", "device_bindings", ["device_id"])
    op.create_index("ix_device_bindings_device_status", "device_bindings", ["device_id", "status"])

    op.create_table(
        "device_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("account_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=False),
        sa.Column("device_id", sa.String(length=64), sa.ForeignKey("devices.device_id"), nullable=False),
        sa.Column("role_id", sa.String(length=128), nullable=False),
        sa.Column("entitlement_tier", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("asr_status", sa.String(length=32), nullable=False),
        sa.Column("llm_status", sa.String(length=32), nullable=False),
        sa.Column("tts_status", sa.String(length=32), nullable=False),
        sa.Column("safety_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("continuity_recall_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_response_latency_ms", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(length=32), nullable=True),
        sa.Column("firmware_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_device_sessions_account_id", "device_sessions", ["account_id"])
    op.create_index("ix_device_sessions_device_id", "device_sessions", ["device_id"])
    op.create_index("ix_device_sessions_state", "device_sessions", ["state"])
    op.create_index("ix_device_sessions_failure_code", "device_sessions", ["failure_code"])
    op.create_index("ix_device_sessions_started_at", "device_sessions", ["started_at"])

    op.create_table(
        "session_transitions",
        sa.Column("transition_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("device_sessions.session_id"), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_session_transitions_session_id", "session_transitions", ["session_id"])
    op.create_index("ix_session_transitions_recorded_at", "session_transitions", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_session_transitions_recorded_at", table_name="session_transitions")
    op.drop_index("ix_session_transitions_session_id", table_name="session_transitions")
    op.drop_table("session_transitions")

    op.drop_index("ix_device_sessions_started_at", table_name="device_sessions")
    op.drop_index("ix_device_sessions_failure_code", table_name="device_sessions")
    op.drop_index("ix_device_sessions_state", table_name="device_sessions")
    op.drop_index("ix_device_sessions_device_id", table_name="device_sessions")
    op.drop_index("ix_device_sessions_account_id", table_name="device_sessions")
    op.drop_table("device_sessions")

    op.drop_index("ix_device_bindings_device_status", table_name="device_bindings")
    op.drop_index("ix_device_bindings_device_id", table_name="device_bindings")
    op.drop_index("ix_device_bindings_account_id", table_name="device_bindings")
    op.drop_table("device_bindings")

    op.drop_index("ix_devices_last_online_at", table_name="devices")
    op.drop_index("ix_devices_bind_status", table_name="devices")
    op.drop_index("ix_devices_owner_account_id", table_name="devices")
    op.drop_table("devices")

    op.drop_table("accounts")

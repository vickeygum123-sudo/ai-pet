"""add continuity memory v0 table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_continuity_memory_v0"
down_revision = "0001_backend_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "continuity_memories",
        sa.Column("memory_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=False),
        sa.Column("source_session_id", sa.String(length=64), sa.ForeignKey("device_sessions.session_id"), nullable=False),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_continuity_memories_user_id", "continuity_memories", ["user_id"])
    op.create_index("ix_continuity_memories_status", "continuity_memories", ["status"])
    op.create_index("ix_continuity_memories_created_at", "continuity_memories", ["created_at"])
    op.create_index("ix_continuity_memories_expires_at", "continuity_memories", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_continuity_memories_expires_at", table_name="continuity_memories")
    op.drop_index("ix_continuity_memories_created_at", table_name="continuity_memories")
    op.drop_index("ix_continuity_memories_status", table_name="continuity_memories")
    op.drop_index("ix_continuity_memories_user_id", table_name="continuity_memories")
    op.drop_table("continuity_memories")

"""add chat threads and household auth"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251008120000_add_chat_threads"
down_revision: Union[str, None] = "20251007160000_add_chat_turns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_threads",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("browser_id", sa.String(length=128), nullable=True),
        sa.Column("household_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("persona", sa.String(length=32), nullable=True),
        sa.Column("lang", sa.String(length=32), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], name="fk_chat_threads_household"),
    )
    op.create_index("ix_chat_threads_browser_id", "chat_threads", ["browser_id"])
    op.create_index("ix_chat_threads_household_id", "chat_threads", ["household_id"])
    op.create_index("ix_chat_threads_archived", "chat_threads", ["archived"])
    op.create_index("ix_chat_threads_last_message_at", "chat_threads", ["last_message_at"])
    op.create_index("ix_chat_threads_created_at", "chat_threads", ["created_at"])

    op.create_table(
        "household_auth",
        sa.Column("household_id", sa.String(length=64), sa.ForeignKey("households.id"), primary_key=True),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("household_auth")
    op.drop_index("ix_chat_threads_created_at", table_name="chat_threads")
    op.drop_index("ix_chat_threads_last_message_at", table_name="chat_threads")
    op.drop_index("ix_chat_threads_archived", table_name="chat_threads")
    op.drop_index("ix_chat_threads_household_id", table_name="chat_threads")
    op.drop_index("ix_chat_threads_browser_id", table_name="chat_threads")
    op.drop_table("chat_threads")

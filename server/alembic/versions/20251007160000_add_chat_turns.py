"""add chat turns table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251007160000_add_chat_turns"
down_revision: Union[str, None] = "20251004145219_add_document_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_turns",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_turns_thread_id", "chat_turns", ["thread_id"])
    op.create_index("ix_chat_turns_created_at", "chat_turns", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_turns_created_at", table_name="chat_turns")
    op.drop_index("ix_chat_turns_thread_id", table_name="chat_turns")
    op.drop_table("chat_turns")

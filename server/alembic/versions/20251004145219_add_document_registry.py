"""add document registry table"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251004145219_add_document_registry"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_registry",
        sa.Column("document_id", sa.String(length=64), primary_key=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("age_range", sa.String(length=32), nullable=False, server_default="all"),
        sa.Column("tone", sa.String(length=32), nullable=False, server_default="supportive"),
        sa.Column("country", sa.String(length=8), nullable=False, server_default="jo"),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="ar"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("s3_uploaded", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_document_registry_topic", "document_registry", ["topic"])
    op.create_index("ix_document_registry_age_range", "document_registry", ["age_range"])


def downgrade() -> None:
    op.drop_index("ix_document_registry_age_range", table_name="document_registry")
    op.drop_index("ix_document_registry_topic", table_name="document_registry")
    op.drop_table("document_registry")

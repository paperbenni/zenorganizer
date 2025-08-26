"""change message_archive.content to Text

Revision ID: ae91783474ca
Revises: 1853843a832e
Create Date: 2025-08-26 21:37:09.905611

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ae91783474ca"
down_revision: Union[str, Sequence[str], None] = "1853843a832e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    SQLite doesn't support ALTER COLUMN TYPE; perform a table-recreate
    migration that creates a new table with the desired TEXT type for
    `content`, copies rows casting the blob to text, then replaces the
    old table.
    """
    # create new table with content as Text
    op.create_table(
        "message_archive_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_time", sa.DateTime(), nullable=False),
    )

    # copy data from old table, casting blob -> text
    op.execute(
        "INSERT INTO message_archive_new (id, content, created_time) "
        "SELECT id, CAST(content AS TEXT), created_time FROM message_archive"
    )

    # drop old table and rename new
    op.drop_table("message_archive")
    op.rename_table("message_archive_new", "message_archive")

    # recreate any indexes/constraints if needed (id primary key preserved)


def downgrade() -> None:
    """Downgrade schema.

    Recreate the table with content as BLOB and copy data back,
    casting TEXT -> BLOB.
    """
    op.create_table(
        "message_archive_old",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content", sa.BLOB(), nullable=False),
        sa.Column("created_time", sa.DateTime(), nullable=False),
    )

    op.execute(
        "INSERT INTO message_archive_old (id, content, created_time) "
        "SELECT id, CAST(content AS BLOB), created_time FROM message_archive"
    )

    op.drop_table("message_archive")
    op.rename_table("message_archive_old", "message_archive")

"""set source file reference to null when a file is deleted

Revision ID: f4b7c0d9e1aa
Revises: 66953fd2a718
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f4b7c0d9e1aa"
down_revision: Union[str, Sequence[str], None] = "66953fd2a718"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("notes_source_file_id_fkey", "notes", type_="foreignkey")
    op.create_foreign_key(
        "notes_source_file_id_fkey",
        "notes",
        "files",
        ["source_file_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("notes_source_file_id_fkey", "notes", type_="foreignkey")
    op.create_foreign_key(
        "notes_source_file_id_fkey",
        "notes",
        "files",
        ["source_file_id"],
        ["id"],
    )
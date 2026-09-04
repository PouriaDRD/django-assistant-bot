"""move backup directory to data

Revision ID: YOUR_REVISION_ID
Revises: 1fb0ea896219
Create Date: 2026-09-04

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "YOUR_REVISION_ID"

down_revision: str | None = "1fb0ea896219"

branch_labels: str | Sequence[str] | None = None

depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Move the default backup directory under data/.

    Custom user-configured backup paths are preserved.
    """

    op.execute("""
        UPDATE app_settings
        SET backup_directory = 'data/backups'
        WHERE backup_directory IN (
            './backups',
            'backups'
        )
        """)


def downgrade() -> None:
    """
    Restore the previous default backup directory.

    Only the new default path is reverted.
    """

    op.execute("""
        UPDATE app_settings
        SET backup_directory = './backups'
        WHERE backup_directory = 'data/backups'
        """)

"""add remember_me to auth_session

Revision ID: a1b2c3d4e5f6
Revises: e6734d9e75b4
Create Date: 2024-07-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e6734d9e75b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add remember_me column to auth_sessions table."""
    # Add remember_me column to auth_sessions table
    op.add_column('auth_sessions', sa.Column('remember_me', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove remember_me column from auth_sessions table."""
    # Remove remember_me column from auth_sessions table
    op.drop_column('auth_sessions', 'remember_me')
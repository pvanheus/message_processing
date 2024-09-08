"""empty message

Revision ID: afae68ff92cb
Revises: 9326df6c209a
Create Date: 2024-09-04 07:49:48.315912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'afae68ff92cb'
down_revision: Union[str, None] = '9326df6c209a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('anon_from_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    op.add_column('messages', sa.Column('anon_from_id'))

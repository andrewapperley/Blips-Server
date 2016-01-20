"""disabled account flag

Revision ID: 317bb0ea4b3c
Revises: 548b22a5d5e
Create Date: 2014-06-30 16:18:02.357121

"""

# revision identifiers, used by Alembic.
revision = '317bb0ea4b3c'
down_revision = '548b22a5d5e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('connections', sa.Column('disabled', sa.SmallInteger))


def downgrade():
    pass

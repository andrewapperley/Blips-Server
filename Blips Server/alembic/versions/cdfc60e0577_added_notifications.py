"""added_notifications

Revision ID: cdfc60e0577
Revises: 1acbe3a6a91
Create Date: 2014-06-03 01:41:59.304448

"""

# revision identifiers, used by Alembic.
revision = 'cdfc60e0577'
down_revision = '1acbe3a6a91'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('notification_users', sa.Column('user_id', sa.Integer))

def downgrade():
    op.drop_column('notification_users', sa.Column('user_id', sa.Integer))

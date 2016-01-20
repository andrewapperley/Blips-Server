"""added_notification_sender

Revision ID: 548b22a5d5e
Revises: 331f3604a692
Create Date: 2014-06-08 21:34:30.596539

"""

# revision identifiers, used by Alembic.
revision = '548b22a5d5e'
down_revision = '331f3604a692'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('notifications', sa.Column('notification_sender', sa.Integer))


def downgrade():
    pass

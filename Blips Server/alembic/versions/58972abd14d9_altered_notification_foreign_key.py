"""altered_notification_foreign_key

Revision ID: 58972abd14d9
Revises: cdfc60e0577
Create Date: 2014-06-03 23:30:19.364817

"""

# revision identifiers, used by Alembic.
revision = '58972abd14d9'
down_revision = 'cdfc60e0577'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column("notification_users", "notification_receiver_id")
    op.drop_column("notifications", "notification_type")
    op.drop_column("notifications", "notification_sender_id")
    op.drop_table("notification_users")
    op.drop_table("notifications")


def downgrade():
    pass

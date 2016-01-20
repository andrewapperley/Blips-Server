"""altered_timelines

Revision ID: 331f3604a692
Revises: 58972abd14d9
Create Date: 2014-06-04 23:07:22.652321

"""

# revision identifiers, used by Alembic.
revision = '331f3604a692'
down_revision = '58972abd14d9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column("notification_users", "notification_receiver_id")
    op.drop_column("timelines", "description")
    op.drop_column("timelines", "cover_image")
    op.drop_column("timelines", "start_date")
    op.drop_column("timelines", "title")


def downgrade():
    pass

"""first_revision

Revision ID: 1acbe3a6a91
Revises: None
Create Date: 2014-05-21 21:35:37.336263

"""

# revision identifiers, used by Alembic.
revision = '1acbe3a6a91'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    return
    op.add_column('timelines', sa.Column('title', sa.String(100)))
    op.add_column('timelines', sa.Column('start_date', sa.DateTime))
    op.add_column('timelines', sa.Column('video_count', sa.Integer))


def downgrade():
    op.drop_column('timelines', 'title')
    op.drop_column('timelines', 'start_date')
    op.drop_column('timelines', 'video_count')

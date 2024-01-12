"""empty message

Revision ID: aecb1ec3281b
Revises: fbc222266ac3
Create Date: 2024-01-12 04:52:14.034813

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aecb1ec3281b'
down_revision = 'fbc222266ac3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('facilities', schema=None) as batch_op:
        batch_op.drop_column('test')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('facilities', schema=None) as batch_op:
        batch_op.add_column(sa.Column('test', sa.INTEGER(), autoincrement=False, nullable=True))

    # ### end Alembic commands ###

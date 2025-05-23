"""Ajout weight

Revision ID: 5f0a2de172bc
Revises: b40a3b367892
Create Date: 2025-05-07 11:02:55.544852

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f0a2de172bc'
down_revision = 'b40a3b367892'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('personal_record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('weight', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('personal_record', schema=None) as batch_op:
        batch_op.drop_column('weight')

    # ### end Alembic commands ###

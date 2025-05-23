"""Ajout de StravaActivity

Revision ID: fa6ac29ef0b8
Revises: 52a4801e0dab
Create Date: 2025-05-10 11:05:14.795560

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa6ac29ef0b8'
down_revision = '52a4801e0dab'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('strava_activity',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('strava_id', sa.BigInteger(), nullable=False),
    sa.Column('hr', sa.Integer(), nullable=True),
    sa.Column('time', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_personal_record_user_id'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('strava_id')
    )
    op.create_table('strava_token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('access_token', sa.String(length=255), nullable=False),
    sa.Column('refresh_token', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.Integer(), nullable=False),
    sa.Column('strava_athlete_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_strava_token_user_id'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('strava_token')
    op.drop_table('strava_activity')
    # ### end Alembic commands ###

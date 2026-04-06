"""add missing repayment schedule fee columns

Revision ID: b1f9478cdf7b
Revises: b74dcd4a5625
Create Date: 2026-03-29 23:35:22.379096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1f9478cdf7b'
down_revision: Union[str, Sequence[str], None] = 'b74dcd4a5625'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('repayment_schedules', sa.Column('grace_period_days', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('repayment_schedules', sa.Column('late_fee_percentage', sa.Numeric(), nullable=True, server_default='0'))
    op.add_column('repayment_schedules', sa.Column('late_fee_charged', sa.Numeric(), nullable=True, server_default='0'))
    op.add_column('repayment_schedules', sa.Column('late_fee_applied', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    op.drop_column('repayment_schedules', 'late_fee_applied')
    op.drop_column('repayment_schedules', 'late_fee_charged')
    op.drop_column('repayment_schedules', 'late_fee_percentage')
    op.drop_column('repayment_schedules', 'grace_period_days')
   
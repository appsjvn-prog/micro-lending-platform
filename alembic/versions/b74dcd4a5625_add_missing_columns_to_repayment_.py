"""add missing columns to repayment_schedules

Revision ID: b74dcd4a5625
Revises: 91b60111f870
Create Date: 2026-03-29 23:30:29.393055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b74dcd4a5625'
down_revision: Union[str, Sequence[str], None] = '91b60111f870'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('repayment_schedules', sa.Column('amount_paid', sa.Numeric(), nullable=True, server_default='0'))
    op.add_column('repayment_schedules', sa.Column('principal_paid', sa.Numeric(), nullable=True, server_default='0'))
    op.add_column('repayment_schedules', sa.Column('interest_paid', sa.Numeric(), nullable=True, server_default='0'))

def downgrade() -> None:
    op.drop_column('repayment_schedules', 'amount_paid')
    op.drop_column('repayment_schedules', 'principal_paid')
    op.drop_column('repayment_schedules', 'interest_paid')
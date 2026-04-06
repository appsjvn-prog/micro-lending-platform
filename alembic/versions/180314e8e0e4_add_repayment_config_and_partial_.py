"""add_repayment_config_and_partial_payments

Revision ID: 180314e8e0e4
Revises: 942385920de6
Create Date: 2026-03-29 15:00:03.374713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '180314e8e0e4'
down_revision: Union[str, Sequence[str], None] = '30c2760b5779'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add columns to loan_products
    op.add_column('loan_products', sa.Column('repayment_frequency', sa.String(20), server_default='MONTHLY', nullable=False))
    op.add_column('loan_products', sa.Column('repayment_day_source', sa.String(30), server_default='DISBURSEMENT_DATE', nullable=False))
    op.add_column('loan_products', sa.Column('grace_period_days', sa.Integer(), server_default='3', nullable=False))
    op.add_column('loan_products', sa.Column('late_fee_percentage', sa.Numeric(5, 2), server_default='2.00', nullable=False))
    
    # Add columns to repayment_schedules
    op.add_column('repayment_schedules', sa.Column('amount_paid', sa.Numeric(10, 2), server_default='0', nullable=False))
    op.add_column('repayment_schedules', sa.Column('principal_paid', sa.Numeric(10, 2), server_default='0', nullable=False))
    op.add_column('repayment_schedules', sa.Column('interest_paid', sa.Numeric(10, 2), server_default='0', nullable=False))
    op.add_column('repayment_schedules', sa.Column('grace_period_days', sa.Integer(), server_default='3', nullable=False))
    op.add_column('repayment_schedules', sa.Column('late_fee_percentage', sa.Numeric(5, 2), server_default='2.00', nullable=False))
    op.add_column('repayment_schedules', sa.Column('late_fee_charged', sa.Numeric(10, 2), server_default='0', nullable=False))
    op.add_column('repayment_schedules', sa.Column('late_fee_applied', sa.Boolean(), server_default='false', nullable=False))
    
    # Add transaction_date
    op.add_column('transactions', sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=True))
    
    # Add new enum values
    op.execute("ALTER TYPE repaymentstatus ADD VALUE IF NOT EXISTS 'PARTIALLY_PAID'")
    op.execute("ALTER TYPE repaymentstatus ADD VALUE IF NOT EXISTS 'PAID_LATE'")
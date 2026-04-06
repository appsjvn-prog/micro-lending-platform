"""add missing columns to loan_products

Revision ID: 91b60111f870
Revises: 180314e8e0e4
Create Date: 2026-03-29 21:51:12.771955
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '91b60111f870'
down_revision = '180314e8e0e4'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("loan_products")]

    if "repayment_frequency" not in columns:
        op.add_column('loan_products', sa.Column('repayment_frequency', sa.String(), nullable=True))

    if "repayment_day_source" not in columns:
        op.add_column('loan_products', sa.Column('repayment_day_source', sa.String(), nullable=True))

    if "grace_period_days" not in columns:
        op.add_column('loan_products', sa.Column('grace_period_days', sa.Integer(), nullable=True, server_default='0'))

    if "late_fee_percentage" not in columns:
        op.add_column('loan_products', sa.Column('late_fee_percentage', sa.Numeric(5, 2), nullable=True, server_default='0'))

    if "status" not in columns:
        op.add_column('loan_products', sa.Column('status', sa.String(), nullable=True, server_default='ACTIVE'))


def downgrade():
    op.drop_column('loan_products', 'updated_by')
    op.drop_column('loan_products', 'created_by')
    op.drop_column('loan_products', 'status')
    op.drop_column('loan_products', 'late_fee_percentage')
    op.drop_column('loan_products', 'grace_period_days')
    op.drop_column('loan_products', 'repayment_day_source')
    op.drop_column('loan_products', 'repayment_frequency')
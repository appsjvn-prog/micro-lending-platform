from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum

class RepaymentStatus(str, Enum):
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    PAID_LATE = "PAID_LATE"
    OVERDUE = "OVERDUE"
    

class RepaymentScheduleResponse(BaseModel):
    """Response for a single repayment schedule"""
    schedule_id: int
    loan_id: UUID
    installment_number: int
    due_date: date
    amount_due: Decimal = Field(example = 15000)
    principal_amount: Decimal
    interest_amount: Decimal
    amount_paid: Decimal = Decimal('0')
    principal_paid: Decimal = Decimal('0')
    interest_paid: Decimal = Decimal('0')
    remaining_amount: Decimal = Field(example = 1500)
    status: RepaymentStatus
    paid_at: Optional[datetime] = None
    grace_period_days: int = 3
    late_fee_percentage: Decimal = Decimal('2.0')
    late_fee_charged: Decimal = Decimal('0')
    late_fee_applied: bool = False
    
    class Config:
        from_attributes = True
    
    @field_validator('amount_due', 'principal_amount', 'interest_amount', 'amount_paid', 'principal_paid', 'interest_paid', 'remaining_amount', 'late_fee_charged', mode='before')
    @classmethod
    def decimal_to_str(cls, v):
        """Convert Decimal to string for JSON response"""
        if v is not None:
            return str(v)
        return v

class RepaymentScheduleListResponse(BaseModel):
    """Response for full repayment schedule list"""
    loan_id: UUID
    total_repayment: str
    total_repaid: str
    remaining_balance: str
    schedules: List[RepaymentScheduleResponse]
    
    class Config:
        from_attributes = True
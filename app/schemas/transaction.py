from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from enum import Enum

class TransactionType(str, Enum):
    DISBURSEMENT = "DISBURSEMENT"
    REPAYMENT = "REPAYMENT"


class TransactionStatus(str, Enum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"

# ---------- Request Schemas ----------

class RepaymentRequest(BaseModel):
    loan_id: UUID
    amount: Decimal = Field(gt=0, description="Amount to repay")
    schedule_id: int = Field(..., description="Installment number to repay (1, 2, 3, etc.)")
    notes: Optional[str] = None

# ---------- Response Schemas ----------
class TransactionResponse(BaseModel):
    id: UUID
    loan_id: UUID
    from_account_id: UUID
    to_account_id: UUID
    amount: Decimal
    type: TransactionType
    status: TransactionStatus
    failure_reason: Optional[str] = None
    reference_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ScheduleUpdateDetail(BaseModel):
    """Details of how a repayment affected a schedule"""
    schedule_id: int
    installment_number: int
    amount_paid: Decimal
    principal_paid: Decimal
    interest_paid: Decimal
    late_fee_charged: Decimal = Decimal('0')
    remaining_amount: Decimal
    status: str

class RepaymentResponse(BaseModel):
    transaction: TransactionResponse
    schedules_updated: List[ScheduleUpdateDetail] = []  # Track all schedules affected
    remaining_balance: Decimal
    message: str
    
    class Config:
        from_attributes = True

# ============== FLEXIBLE REPAYMENT SCHEMAS ==============

class FlexibleRepaymentRequest(BaseModel):
    """Request for flexible repayment - pay ANY amount"""
    amount: Decimal = Field(..., gt=0, description="Any amount - auto-allocated to oldest pending EMIs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1500.00
            }
        }


class FlexibleRepaymentAllocation(BaseModel):
    """Individual allocation details"""
    installment_number: int
    amount_paid: Decimal
    type: str  # "FULL" or "PARTIAL"
    penalty_included: Decimal = Decimal('0')
    remaining_due: Optional[Decimal] = None


class FlexibleRepaymentResponse(BaseModel):
    """Response for flexible repayment"""
    success: bool
    loan_id: str
    payment_amount: float
    amount_allocated: float
    remaining_balance: float
    loan_status: str
    transaction_id: str
    reference_number: str
    allocations: List[FlexibleRepaymentAllocation]
    is_loan_fully_paid: bool
    message: str
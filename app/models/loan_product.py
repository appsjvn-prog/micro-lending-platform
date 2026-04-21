from sqlalchemy import Column, String, Numeric, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SQLEnum
from app.core.database import Base
from app.core.timezone import utc_now  
import uuid
import enum


from app.models.base import AuditMixin 
from app.core.enums import CaseInsensitiveEnum

class InterestType(CaseInsensitiveEnum):
    FLAT = "FLAT"

class LoanProductStatus(CaseInsensitiveEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class RepaymentFrequency(CaseInsensitiveEnum):
    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"

class RepaymentDaySource(CaseInsensitiveEnum):
    APPLICATION_DATE = "APPLICATION_DATE"
    DISBURSEMENT_DATE = "DISBURSEMENT_DATE"


class LoanProduct(Base, AuditMixin):
    __tablename__ = "loan_products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    
    # Amount range
    min_amount = Column(Numeric(10, 2), nullable=False)
    max_amount = Column(Numeric(10, 2), nullable=False)
    
    # Tenure range (in months)
    min_tenure_months = Column(Integer, nullable=False)
    max_tenure_months = Column(Integer, nullable=False)
    
    # Interest configuration
    interest_type = Column(SQLEnum(InterestType), nullable=False, default=InterestType.FLAT)
    min_interest_rate = Column(Numeric(5, 2), nullable=False)  # e.g., 5.5%
    max_interest_rate = Column(Numeric(5, 2), nullable=False)  # e.g., 15.5%

    #  REPAYMENT CONFIG
    repayment_frequency = Column(SQLEnum(RepaymentFrequency), nullable=False, default=RepaymentFrequency.MONTHLY)
    repayment_day_source = Column(SQLEnum(RepaymentDaySource), nullable=False, default=RepaymentDaySource.DISBURSEMENT_DATE)
    grace_period_days = Column(Integer, nullable=False, default=3)
    late_fee_percentage = Column(Numeric(5, 2), nullable=False, default=2.0)
    
    # Status
    status = Column(SQLEnum(LoanProductStatus), nullable=False, default=LoanProductStatus.ACTIVE)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
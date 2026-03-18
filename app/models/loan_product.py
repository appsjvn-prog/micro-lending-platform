from sqlalchemy import Column, String, Enum, Numeric, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from datetime import datetime, timezone

from app.core.database import Base
from app.core.timezone import utc_now   

class InterestType(str, enum.Enum):
    FLAT = "FLAT"
    REDUCING = "REDUCING"
    SIMPLE = "SIMPLE"
    COMPOUND = "COMPOUND"

class LoanProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class LoanProduct(Base):
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
    interest_type = Column(Enum(InterestType), nullable=False)
    min_interest_rate = Column(Numeric(5, 2), nullable=False)  # e.g., 5.5%
    max_interest_rate = Column(Numeric(5, 2), nullable=False)  # e.g., 15.5%
    
    # Status
    status = Column(Enum(LoanProductStatus), nullable=False, default=LoanProductStatus.ACTIVE)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

from app.models.lender_profile import RiskAppetite, LenderStatus
from app.models.borrower_profile import EmploymentType

# Create/Update Schemas (Input) 
class LenderProfileBase(BaseModel):
    """What user submits when creating/updating profile"""
    profile_name: str = Field(..., max_length=100)
    business_type: str = Field(..., max_length=50)
    risk_appetite: RiskAppetite

class LenderProfileCreate(LenderProfileBase):
    pass

class LenderProfileUpdate(BaseModel):
    """Update schema - all fields optional"""
    profile_name: Optional[str] = Field(None, max_length=100)
    business_type: Optional[str] = Field(None, max_length=50)
    risk_appetite: Optional[RiskAppetite] = None

#  Standard Response (for most operations)
class LenderProfileResponse(BaseModel):
    """Standard lender profile response"""
    id: UUID
    user_id: UUID
    profile_name: Optional[str] = None
    business_type: Optional[str] = None
    risk_appetite: RiskAppetite
    status: LenderStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Minimal Response (for POST) 
class LenderProfileMinimalResponse(BaseModel):
    """What user sees after create/update"""
    id: UUID
    profile_name: Optional[str] = None
    status: LenderStatus
    is_verified: bool
    created_at: datetime
    message: str = "Lender profile created successfully"

    class Config:
        from_attributes = True

#  Self View (what lender sees) 
class LenderProfileSelfResponse(BaseModel):
    """Lender sees their own profile"""
    id: UUID
    profile_name: Optional[str] = None
    business_type: Optional[str] = None
    risk_appetite: RiskAppetite
    status: LenderStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Admin Response (full details) 
class LenderProfileAdminResponse(BaseModel):
    """Admin view - includes all fields"""
    id: UUID
    user_id: UUID
    profile_name: Optional[str] = None
    business_type: Optional[str] = None
    risk_appetite: RiskAppetite
    status: LenderStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


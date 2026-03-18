from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from typing import List
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.lender_profile import LenderProfile
from app.schemas.lender_profile import (
    LenderProfileCreate,
    LenderProfileUpdate,
    LenderProfileResponse,
    LenderProfileMinimalResponse
)
from app.core.exceptions import AppException, NotFoundException, UnauthorizedException
from app.core.timezone import utc_now 

router = APIRouter(prefix="/lender", tags=["Lender"])

# Helper function
def check_user_profile_exists(current_user: User, db: Session):
    """Check if user has a profile before creating lender profile"""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise AppException( 
            "Please complete your user profile first",
            status_code=400
        )
    return profile

@router.post("/profile", response_model=LenderProfileMinimalResponse, status_code=status.HTTP_201_CREATED)
def create_lender_profile(
    profile_data: LenderProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create lender profile.
    
    - Requires LENDER role
    - User profile must exist first
    - One profile per user
    """
    # Check role
    if current_user.role != "LENDER":
        raise UnauthorizedException("create lender profiles")
    
    # Check user profile exists
    check_user_profile_exists(current_user, db)
    
    # Check if lender profile already exists
    existing = db.query(LenderProfile).filter(
        LenderProfile.user_id == current_user.id
    ).first()
    
    if existing:
        raise AppException(
            "You already have a lender profile",
            status_code=400
        )
    
    # Create profile (simplified - no balance fields needed)
    db_profile = LenderProfile(
        user_id=current_user.id,
        profile_name=profile_data.profile_name,
        business_type=profile_data.business_type,
        default_min_amount=profile_data.default_min_amount,
        default_max_amount=profile_data.default_max_amount,
        default_min_tenure=profile_data.default_min_tenure,
        default_max_tenure=profile_data.default_max_tenure,
        default_interest_rate=profile_data.default_interest_rate,
        risk_appetite=profile_data.risk_appetite
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    
    return {
        "id": db_profile.id,
        "profile_name": db_profile.profile_name,
        "status": db_profile.status,
        "is_verified": db_profile.is_verified,
        "created_at": db_profile.created_at,
        "message": "Lender profile created successfully"
    }

@router.get("/profiles", response_model=List[LenderProfileResponse])
def get_lender_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Remove .options(joinedload(...))
    query = db.query(LenderProfile)  # 👈 Simpler query
    
    if current_user.role == "ADMIN":
        return query.all()
    
    elif current_user.role == "LENDER":
        profile = query.filter(LenderProfile.user_id == current_user.id).first()
        return [profile] if profile else []
    
    return []

@router.put("/profile/me", response_model=LenderProfileResponse)
def update_lender_profile(
    profile_update: LenderProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update your lender profile.
    
    All fields are optional - only send fields you want to update.
    """
    if current_user.role != "LENDER":
        raise UnauthorizedException("update lender profiles")
    
    profile = db.query(LenderProfile).filter(
        LenderProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise  NotFoundException("Lender profile")
    
    # Update fields
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    profile.updated_at = utc_now()
    db.commit()
    db.refresh(profile)
    
    return profile


@router.patch("/profiles/{profile_id}/verify", response_model=LenderProfileResponse)
def verify_lender_profile(
    profile_id: UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Verify a lender profile (admin only).
    
    Marks lender as verified so they can create loan offers.
    """
    profile = db.query(LenderProfile).filter(
        LenderProfile.id == profile_id
    ).first()
    
    if not profile:
        raise NotFoundException("Lender profile")
    
    profile.is_verified = True
    profile.updated_at = utc_now()
    db.commit()
    db.refresh(profile)
    
    return profile


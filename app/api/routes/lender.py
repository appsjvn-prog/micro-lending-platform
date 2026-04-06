from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile
from app.models.lender_profile import LenderProfile, LenderStatus
from app.schemas.lender_profile import (
    LenderProfileCreate,
    LenderProfileUpdate,
    LenderProfileResponse,
    LenderProfileMinimalResponse,
    LenderProfileSelfResponse,
    LenderProfileAdminResponse
)
from app.core.exceptions import (
    AppException,
    NotFoundException, 
    UnauthorizedException,  
    LenderProfileNotFoundException
)
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
    if current_user.role != UserRole.LENDER:
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
    
    # Create profile
    db_profile = LenderProfile(
        user_id=current_user.id,
        profile_name=profile_data.profile_name,
        business_type=profile_data.business_type,
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

@router.get("/profiles")
def get_lender_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lender profiles:
    - LENDER: Returns their own profile
    - ADMIN: Returns all profiles
    - BORROWER: Returns public info only
    """
    
    # Admin: return all profiles
    if current_user.role == UserRole.ADMIN:
        profiles = db.query(LenderProfile).options(
            selectinload(LenderProfile.user)
        ).all()
        
        return [
            LenderProfileAdminResponse(
                id=p.id,
                user_id=p.user_id,
                profile_name=p.profile_name,
                business_type=p.business_type,
                risk_appetite=p.risk_appetite,
                status=p.status,
                is_verified=p.is_verified,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in profiles
        ]
    
    if current_user.role == UserRole.BORROWER:
        profiles = db.query(LenderProfile).filter(
            LenderProfile.is_verified == True,
            LenderProfile.status == LenderStatus.ACTIVE
        ).all()
        
        return [
            {
                "id": str(p.id),
                "profile_name": p.profile_name,
                "business_type": p.business_type,
                "risk_appetite": p.risk_appetite,
                "is_verified": p.is_verified
            }
            for p in profiles
        ]
    
    # Get profile for current user
    profile = db.query(LenderProfile).filter(
        LenderProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Lender profile not found"
        )
    
    # Return appropriate response based on role
    if current_user.role == UserRole.LENDER:
        # Lender sees their own full profile
        return LenderProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            profile_name=profile.profile_name,
            business_type=profile.business_type,
            risk_appetite=profile.risk_appetite,
            status=profile.status,
            is_verified=profile.is_verified,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
   
@router.put("/profile", response_model=LenderProfileResponse)
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
        raise NotFoundException("Lender profile")
    
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

@router.delete("/profile", status_code=status.HTTP_200_OK)
def delete_lender_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete your lender profile.
    
    This removes lender-specific data but keeps user account.
    Cannot be undone.
    """
    # Check role
    if current_user.role != UserRole.LENDER:
        raise UnauthorizedException("delete lender profiles")
    
    # Find profile
    profile = db.query(LenderProfile).filter(
        LenderProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise LenderProfileNotFoundException()
    
    # Delete profile
    db.delete(profile)
    db.commit()
    
    return {
        "success": True,
        "message": "Lender profile deleted successfully"
    }
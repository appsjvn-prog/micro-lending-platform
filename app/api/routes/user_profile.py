from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    UserProfileMinimalResponse
)
from app.schemas.user import PhoneNumber
from app.core.exceptions import AppException, NotFoundException, UnauthorizedException, ValidationException
from app.core.timezone import utc_now

router = APIRouter(prefix="/user/profile", tags=["User Profile"])

@router.post("", response_model=UserProfileMinimalResponse, status_code=status.HTTP_201_CREATED)
def create_user_profile(
    profile: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create user profile (personal information).
    
    - Required for ALL users (borrowers and lenders)
    - One profile per user
    - Must be created before borrower/lender profiles
    """

     # ✅ SECURITY CHECK: Phone number must match registered phone
    if (profile.mobile.country_code != current_user.country_code or 
        profile.mobile.national_number != current_user.national_number):
         raise ValidationException(
            "Primary phone number must match the registered phone number"
        )
    
    # Check if profile already exists
    existing = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    if existing:
         raise AppException(  # 👈 Change to AppException
            "You already have a user profile",
            status_code=400
         )
    
    # Create profile
    db_profile = UserProfile(
        user_id=current_user.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        dob=profile.dob,
        gender=profile.gender,
        email=profile.email,
        country_code=profile.mobile.country_code,
        national_number=profile.mobile.national_number
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    
    return {
        "id": db_profile.id,
        "created_at": db_profile.created_at,
        "message": "User profile created successfully"
    }

@router.get("/profiles", response_model=List[UserProfileResponse])
def get_user_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user profiles based on role:
    - Any authenticated user: Returns their own profile
    - ADMIN: Returns all profiles
    """
    if current_user.role == "ADMIN":
        # Admin sees all
        return db.query(UserProfile).all()
    
    # Regular user sees only their own
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    return [profile] if profile else []

@router.put("", response_model=UserProfileResponse)
def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update your user profile.
    
    All fields are optional - only send fields you want to update.
    """
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise NotFoundException("User profile")
    
    # Update fields
    update_data = profile_update.model_dump(exclude_unset=True)
    
    # Handle phone number updates
    if 'mobile' in update_data:
        mobile = update_data.pop('mobile')
        profile.country_code = mobile.get('country_code')
        profile.national_number = mobile.get('national_number')
    
    # Handle alternate mobile
    if 'alternate_mobile' in update_data:
        alt_mobile = update_data.pop('alternate_mobile')
        if alt_mobile:
            profile.alternate_country_code = alt_mobile.get('country_code')
            profile.alternate_national_number = alt_mobile.get('national_number')
        else:
            profile.alternate_country_code = None
            profile.alternate_national_number = None
    
    # Handle other fields
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    profile.updated_at = utc_now()
    db.commit()
    db.refresh(profile)

    db.refresh(profile)
    
    return profile

@router.delete("", status_code=status.HTTP_200_OK)
def delete_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete your user profile.
    
    This will also cascade delete addresses.
    Cannot be undone.
    """
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise NotFoundException("User profile")
    
    db.delete(profile)
    db.commit()
    
    return {
        "success": True,
        "message": "User profile deleted successfully"
    }




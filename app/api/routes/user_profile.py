from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Union
from datetime import date

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
from app.core.exceptions import(
    AppException, 
    NotFoundException, 
    UnauthorizedException, 
    ValidationException,
    ProfileNotFoundException,
    ProfileAlreadyExistsException,
    ProfilePhoneMismatchException,
    ProfileEmailMismatchException)
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
    """

    # SECURITY: Email in profile must match authenticated user's email
    if profile.email != current_user.email:
        raise ProfileEmailMismatchException()
    
    # SECURITY CHECK: Phone number must match registered phone
    if (profile.mobile.country_code != current_user.country_code or 
        profile.mobile.national_number != current_user.national_number):
        raise ProfilePhoneMismatchException()
    
    # Check if profile already exists
    existing = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    if existing:
         raise ProfileAlreadyExistsException()
    
    try:
    #  FIX - Add alternate mobile fields
        alternate_country_code = None
        alternate_national_number = None
        if profile.alternate_mobile:
            alternate_country_code = profile.alternate_mobile.country_code
            alternate_national_number = profile.alternate_mobile.national_number
    
        # Create profile
        db_profile = UserProfile(
            user_id=current_user.id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            dob=profile.dob,
            gender=profile.gender,
            email=profile.email,
            marital_status=profile.marital_status,
            nationality=profile.nationality,
            country_code=profile.mobile.country_code,
            national_number=profile.mobile.national_number,
            alternate_country_code=alternate_country_code,
            alternate_national_number=alternate_national_number,
            created_at=utc_now(),
            updated_at=utc_now()
        )
    
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
    
        return {
            "id": db_profile.id,
            "created_at": db_profile.created_at,
            "updated_at": db_profile.updated_at,
            "message": "User profile created successfully"
        }
    except Exception as e:
        db.rollback()
        raise AppException(f"Failed to create user profile: {str(e)}",
                           status_code=status)

@router.get("", response_model=Union[UserProfileResponse,List[UserProfileResponse]])
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
        profiles = db.query(UserProfile).all()
        return profiles
    
    # Regular user sees only their own
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise ProfileNotFoundException()
    
    return profile

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
        raise ProfileNotFoundException()
    
    try:
    
        # Update fields
        update_data = profile_update.model_dump(exclude_unset=True)
        
        # Handle phone number updates
        if 'mobile' in update_data:
            mobile = update_data.pop('mobile')

            if( mobile.get('country_code') != current_user.country_code or
                mobile.get('national_number') != current_user.national_number):
                raise ProfilePhoneMismatchException()
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
    
    except (ProfilePhoneMismatchException, ProfileNotFoundException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(f"Failed to update user profile: {str(e)}",
                           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        raise ProfileNotFoundException()
    
    try:
    
        db.delete(profile)
        db.commit()
        
        return {
            "success": True,
            "message": "User profile deleted successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to delete user profile: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





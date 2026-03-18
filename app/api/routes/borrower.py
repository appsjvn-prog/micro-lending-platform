from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from datetime import datetime 
from sqlalchemy.orm import joinedload 
 


from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.borrower_profile import BorrowerProfile 
from app.schemas.borrower_profile import (
    BorrowerProfileCreate,
    BorrowerProfileUpdate,
    BorrowerProfileResponse,
    BorrowerProfileMinimalResponse
)
from app.core.exceptions import AppException, NotFoundException, UnauthorizedException
from app.core.timezone import utc_now

router = APIRouter(prefix="/borrower", tags=["Borrower"])

# Helper function
def check_user_profile_exists(current_user: User, db: Session):
    """Check if user has a profile before creating borrower profile"""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise AppException(
            "Please complete your user profile first",
            status_code=400
        )
    return profile

@router.post("/profile", response_model= BorrowerProfileMinimalResponse , status_code=status.HTTP_201_CREATED)
def create_borrower_profile(
    profile_data: BorrowerProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create borrower profile.
    
    - Requires BORROWER role
    - User profile must exist first
    - One profile per user
    - Employment type and monthly income are required
    """
    # Check role
    if current_user.role != "BORROWER":
        raise UnauthorizedException("Create borrower profiles")
    
    # Check user profile exists
    check_user_profile_exists(current_user, db)
    
    # Check if borrower profile already exists
    existing = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if existing:
        raise AppException(  # 👈 Change to AppException
            "You already have a borrower profile",
            status_code=400
        )
    
    # Create profile
    db_profile = BorrowerProfile(
        user_id=current_user.id,
        employment_type=profile_data.employment_type,
        monthly_income=profile_data.monthly_income,
        employer_name=profile_data.employer_name,
        current_job_tenure_months=profile_data.current_job_tenure_months,
        total_work_experience_years=profile_data.total_work_experience_years,
        preferred_max_interest_rate=profile_data.preferred_max_interest_rate,
        preferred_min_amount=profile_data.preferred_min_amount,
        preferred_max_amount=profile_data.preferred_max_amount,
        preferred_tenure_months=profile_data.preferred_tenure_months
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    
    return db_profile

@router.get("/profiles", response_model=List[BorrowerProfileResponse])
def get_borrower_profiles(
    current_user: User = Depends(get_current_user),  # Not just admin
    db: Session = Depends(get_db)
):
    """
    Get borrower profiles.
    - BORROWER: Returns their own profile (as a list with 1 item)
    - ADMIN: Returns all profiles
    """
    query = db.query(BorrowerProfile).options(joinedload(BorrowerProfile.user))
    
    if current_user.role == "ADMIN":
        # Admin sees all
        profiles = query.all()
        return profiles
    
    elif current_user.role == "BORROWER":
        # Borrower sees only their own
        profile = query.filter(
            BorrowerProfile.user_id == current_user.id
        ).first()
        return [profile] if profile else []
    
    else:
        return []

@router.put("/profile/me", response_model=BorrowerProfileResponse)
def update_borrower_profile(
    profile_update: BorrowerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update your borrower profile.
    
    All fields are optional - only send fields you want to update.
    """
    if current_user.role != "BORROWER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only borrowers can update borrower profiles"
        )
    
    profile = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower profile not found"
        )
    
    # Update fields
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    profile.updated_at = utc_now()
    db.commit()
    db.refresh(profile)
    
    return profile

@router.delete("/profile/me", status_code=status.HTTP_200_OK)
def delete_borrower_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete your borrower profile.
    
    This removes borrower-specific data but keeps user account.
    Cannot be undone.
    """
    if current_user.role != "BORROWER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only borrowers can delete borrower profiles"
        )
    
    profile = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower profile not found"
        )
    
    db.delete(profile)
    db.commit()
    
    return  {
        "success": True,
        "message": "Borrower profile deleted successfully"
    }

# ---------- Admin Endpoints ----------
# @router.get("/profiles/user/{user_id}", response_model=BorrowerProfileResponse)
# def get_borrower_profile_by_user_id(
#     user_id: UUID,
#     admin: User = Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get borrower profile by user ID (admin only).
    
#     Returns profile for a specific borrower.
#     """
#     profile = db.query(BorrowerProfile).filter(
#         BorrowerProfile.user_id == user_id
#     ).first()
    
#     if not profile:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Borrower profile not found for this user"
#         )
    
#     return profile

# @router.get("/stats/simple", response_model=dict)
# def get_simple_borrower_stats(
#     admin: User = Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get basic borrower statistics (admin only).
    
#     Returns count of borrowers by employment type.
#     """
#     total = db.query(BorrowerProfile).count()
    
#     # Count by employment type
#     salaried = db.query(BorrowerProfile).filter(
#         BorrowerProfile.employment_type == "SALARIED"
#     ).count()
    
#     self_employed = db.query(BorrowerProfile).filter(
#         BorrowerProfile.employment_type == "SELF_EMPLOYED"
#     ).count()
    
#     business = db.query(BorrowerProfile).filter(
#         BorrowerProfile.employment_type == "BUSINESS"
#     ).count()
    
#     return {
#         "total_borrowers": total,
#         "by_employment_type": {
#             "SALARIED": salaried,
#             "SELF_EMPLOYED": self_employed,
#             "BUSINESS": business
#         }
#     }

# # Optional: Filter borrowers by income range (admin only)
# @router.get("/profiles/filter/income", response_model=List[BorrowerProfileResponse])
# def filter_borrowers_by_income(
#     min_income: float,
#     max_income: float,
#     admin: User = Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ):
#     """
#     Filter borrowers by monthly income range (admin only).
    
#     - min_income: Minimum monthly income
#     - max_income: Maximum monthly income
#     """
#     if min_income > max_income:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Min income cannot be greater than max income"
#         )
    
#     profiles = db.query(BorrowerProfile).filter(
#         BorrowerProfile.monthly_income >= min_income,
#         BorrowerProfile.monthly_income <= max_income
#     ).all()
    
#     return profiles
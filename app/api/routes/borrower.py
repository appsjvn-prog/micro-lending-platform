from unicodedata import numeric

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Union
from datetime import datetime 
from sqlalchemy.orm import joinedload 
 


from app.core.database import get_db
from app.api.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile
from app.models.borrower_profile import BorrowerProfile 
from app.schemas.borrower_profile import (
    BorrowerProfileCreate,
    BorrowerProfileUpdate,
    BorrowerProfileResponse,
    BorrowerProfileMinimalResponse,
    LenderBorrowerViewResponse
)
from app.core.exceptions import (
    AppException,
    NotFoundException, 
    UnauthorizedException,
    ProfileAlreadyExistsException,
    ProfileNotFoundException 
)  
from app.core.timezone import utc_now
from app.services.risk_score import RiskScoreCalculator

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
    if current_user.role != UserRole.BORROWER:
        raise UnauthorizedException("Create borrower profiles")
    
    # Check user profile exists
    check_user_profile_exists(current_user, db)
    
    # Check if borrower profile already exists
    existing = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if existing:
        raise ProfileAlreadyExistsException()
    
    # Create profile
    db_profile = BorrowerProfile(
        user_id=current_user.id,
        employment_type=profile_data.employment_type,
        monthly_income=profile_data.monthly_income,
        employer_name=profile_data.employer_name,
        current_job_tenure_months=profile_data.current_job_tenure_months,
        total_work_experience_years=profile_data.total_work_experience_years
    )
    
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    
    return db_profile

@router.get("/profiles", response_model=List[Union[BorrowerProfileResponse, LenderBorrowerViewResponse]])
def get_borrower_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get borrower profiles.
    - BORROWER: Returns their own profile (as a list with 1 item)
    - ADMIN: Returns all profiles
    - LENDER: Returns limited profiles with risk score
    """
    query = db.query(BorrowerProfile).options(joinedload(BorrowerProfile.user))
    risk_calc = RiskScoreCalculator(db)
    
    if current_user.role == UserRole.ADMIN:
        # Admin sees all
        profiles = query.all()
        result = []
        for profile in profiles:
            risk_result = risk_calc.calculate_risk_score(str(profile.user_id))
            result.append(_build_profile_response(profile, risk_result, include_sensitive=True))
        return result
        
    elif current_user.role == UserRole.BORROWER:
        profile = query.filter(BorrowerProfile.user_id == current_user.id).first()
        if not profile:
            return []
        risk_result = risk_calc.calculate_risk_score(str(current_user.id))
        #  FIXED: Use risk_result, not empty dict
        return [_build_profile_response(profile, risk_result, include_sensitive=True)]
  
    elif current_user.role == UserRole.LENDER:
        # Lender sees all borrower profiles but limited data + risk score
        profiles = query.all()
        result = []
        for profile in profiles:
            risk_result = risk_calc.calculate_risk_score(str(profile.user_id), for_lender=True)
            if "error" not in risk_result:
                result.append(_build_lender_view_response(profile, risk_result))
        return result
    
    else:
        return []
    
@router.get("/risk-score")
def get_my_risk_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick endpoint to get just your risk score (no profile data).
    """
    if current_user.role != "BORROWER":
        return {"message": "Risk score is only relevant for borrowers"}
    
    risk_calc = RiskScoreCalculator(db)
    result = risk_calc.calculate_risk_score(str(current_user.id))
    
    if "error" in result:
        raise NotFoundException(result["error"])
    
    return {
        "risk_score": result["score"],
        "risk_level": result["risk_level"],
        "factors": result.get("breakdown")
    }


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
    if current_user.role != UserRole.BORROWER:
        raise UnauthorizedException()


    profile = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise ProfileNotFoundException()
    
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    profile.updated_at = utc_now()
    db.commit()
    db.refresh(profile)
    
    risk_calc = RiskScoreCalculator(db)
    risk_result = risk_calc.calculate_risk_score(str(current_user.id))

    return _build_profile_response(profile, risk_result, include_sensitive=True)
    

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
        raise UnauthorizedException()
    
    profile = db.query(BorrowerProfile).filter(
        BorrowerProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise ProfileNotFoundException()
    
    db.delete(profile)
    db.commit()
    
    return  {
        "success": True,
        "message": "Borrower profile deleted successfully"
    }

# ============== HELPER FUNCTIONS ==============

def _build_profile_response(profile: BorrowerProfile, risk_result: dict, include_sensitive: bool = False) -> dict:
    """Build response for borrower profile with risk score"""

    response ={
        "id": profile.id,
        "user_id": profile.user_id,
        "employment_type": profile.employment_type.value if profile.employment_type else None,
        "monthly_income": float(profile.monthly_income) if profile.monthly_income else None,
        "employer_name": profile.employer_name,
        "total_work_experience_years": profile.total_work_experience_years,
        "current_job_tenure_months": profile.current_job_tenure_months,
        "is_profile_complete": profile.is_profile_complete,
        "created_at": profile.created_at,   
        "updated_at": profile.updated_at,
    }
    
    #  Always add risk score if available (even for non-sensitive view)
    if risk_result and "error" not in risk_result:
        response["risk_score"] = risk_result.get("score")
        response["risk_level"] = risk_result.get("risk_level")
        if include_sensitive:
            response["risk_breakdown"] = risk_result.get("breakdown")
    else:
        # Add default None values so the field exists in response
        response["risk_score"] = None
        response["risk_level"] = None
    
    return response
    

def _build_lender_view_response(profile: BorrowerProfile, risk_result: dict) -> dict:
    """Build response for lender view (limited data)"""
    return {
        "id": profile.id,
        "employment_type": profile.employment_type.value if profile.employment_type else None,
        "risk_score": risk_result.get("score") if "error" not in risk_result else None,
        "risk_level": risk_result.get("risk_level") if "error" not in risk_result else None,
        "is_profile_complete": profile.is_profile_complete,
    }

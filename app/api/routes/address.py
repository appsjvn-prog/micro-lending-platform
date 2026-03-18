from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.address import Address
from app.schemas.address import AddressCreate, AddressResponse
from app.core.exceptions import AppException, NotFoundException

router = APIRouter(prefix="/addresses", tags=["Addresses"])

# Helper
def get_user_profile(current_user: User, db: Session):
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise AppException("Please create your user profile before adding addresses", status_code=400)
    return profile

@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    address: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an address"""
    profile = get_user_profile(current_user, db)
    
    # First address becomes primary automatically
    is_primary = address.is_primary
    if db.query(Address).filter(Address.user_profile_id == profile.id).count() == 0:
        is_primary = True
    
    db_address = Address(
        user_profile_id=profile.id,
        **address.dict()
    )
    db.add(db_address)
    db.commit()
    db.refresh(db_address)
    return db_address

@router.get("", response_model=List[AddressResponse])
def get_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all my addresses"""
    profile = get_user_profile(current_user, db)
    return db.query(Address).filter(
        Address.user_profile_id == profile.id
    ).all()

@router.delete("/{address_id}", status_code=status.HTTP_200_OK)
def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an address"""
    profile = get_user_profile(current_user, db)
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_profile_id == profile.id
    ).first()
    
    if not address:
        raise NotFoundException("Address")
    
    db.delete(address)
    db.commit()
    return  {
        "success": True,
        "message": "Address deleted successfully"
    }
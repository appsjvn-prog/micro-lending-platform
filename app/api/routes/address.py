from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.address import Address
from app.schemas.address import AddressCreate, AddressResponse, AddressCreateResponse
from app.core.exceptions import(
    AppException,
    AddressNotFoundException,
    AddressLimitExceededException,
    DuplicateAddressException,

)
from app.core.timezone import utc_now

MAX_ADDRESSES_PER_USER = 3

router = APIRouter(prefix="/addresses", tags=["Addresses"])

# Helper
def get_user_profile(current_user: User, db: Session):
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise AppException("Please create your user profile before adding addresses", status_code=400)
    return profile
def is_duplicate_address(profile_id: UUID, address_data: dict, db: Session, exclude_id: UUID = None) -> bool:
    """
    Check if address already exists for the user profile.
    
    Compares address_line1, city, state, pincode (most critical fields)
    """
    query = db.query(Address).filter(
        Address.user_profile_id == profile_id,
        Address.address_line1.ilike(address_data.get("address_line1")),
        Address.city.ilike(address_data.get("city")),
        Address.state.ilike(address_data.get("state")),
        Address.pincode == address_data.get("pincode")
    )
    
    # Exclude current address when updating
    if exclude_id:
        query = query.filter(Address.id != exclude_id)
    
    return query.first() is not None


def normalize_address_for_comparison(address: AddressCreate) -> dict:
    """Normalize address fields for comparison (case-insensitive, trim spaces)"""
    return {
        "address_line1": address.address_line1.strip().lower(),
        "city": address.city.strip().lower(),
        "state": address.state.strip().lower(),
        "pincode": address.pincode.strip(),
    }

@router.post("", response_model=AddressCreateResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    address: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an address"""
    
    profile = get_user_profile(current_user, db)

    address_data = {
        "address_line1": address.address_line1,
        "city": address.city,
        "state": address.state,
        "pincode": address.pincode
    }

    if is_duplicate_address(profile.id, address_data, db):
        raise DuplicateAddressException()
    
    existing_addresses = db.query(Address).filter(
    Address.user_profile_id == profile.id).count()
    
    if existing_addresses >= MAX_ADDRESSES_PER_USER:
        raise AddressLimitExceededException()
    
    is_primary = address.is_primary

    if existing_addresses == 0:
        is_primary = True

    if is_primary and existing_addresses > 0:
        db.query(Address).filter(
            Address.user_profile_id == profile.id,
            Address.is_primary == True
        ).update({"is_primary": False})
    
    db_address = Address(
        user_profile_id=profile.id,
        address_type=address.address_type,
        is_primary=is_primary,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        landmark=address.landmark,
        city=address.city,
        state=address.state,
        district=address.district,
        pincode=address.pincode,
        country=address.country,
        created_at=utc_now(),
        updated_at=utc_now()
    )

    db.add(db_address)
    db.commit()
    db.refresh(db_address)

    return AddressCreateResponse(
        id=db_address.id,
        address_type=db_address.address_type,
        is_primary=db_address.is_primary,
        city=db_address.city,
        state=db_address.state,
        message="Address created successfully"
    )


@router.get("", response_model=List[AddressResponse])
def get_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all my addresses"""

    profile = get_user_profile(current_user, db)

    addresses = db.query(Address).filter(
        Address.user_profile_id == profile.id).order_by(Address.created_at.desc()).all()
    
    return addresses


@router.delete("/{address_id}", status_code=status.HTTP_200_OK)
def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an address"""

    profile = get_user_profile(current_user, db)

    try:
        address_uuid = UUID(address_id)
    except ValueError:
        raise AppException("Invalid address ID format", status_code=400)
    
    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_profile_id == profile.id
    ).first()
    
    if not address:
        raise AddressNotFoundException()
    
    was_primary = address.is_primary
    
    db.delete(address)

    if was_primary:
        next_address = db.query(Address).filter(
            Address.user_profile_id == profile.id
        ).order_by(Address.created_at.desc()).first()
        
        if next_address:
            next_address.is_primary = True
            next_address.updated_at = utc_now()

    db.commit()

    return  {
        "success": True,
        "message": "Address deleted successfully"
    }
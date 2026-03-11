"""
🔜 WEEK 3 FEATURE - Auth Dependencies
This module contains authentication dependencies for protecting endpoints.
For Week 2, we're adding a simple admin check that will be replaced in Week 3.
"""
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from typing import Optional

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ---------- WEEK 2: Simple Admin Header Protection ----------
# This will be replaced with proper JWT admin check in Week 3
ADMIN_SECRET_KEY = "adminkey"  # In production, use environment variable

async def verify_admin_header(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    """
    WEEK 2: Simple admin verification using header
    🔜 WEEK 3: This will be replaced with proper JWT admin check
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin key required"
        )
    
    if x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )
    
    return True

# ---------- WEEK 3: Proper JWT Authentication ----------
# These will be used in Week 3 when JWT is implemented

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    🔜 WEEK 3: Get current authenticated user from token
    Not used in Week 2
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    🔜 WEEK 3: Get current user and verify they are active
    """
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user

async def get_current_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    🔜 WEEK 3: Verify current user is an admin
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
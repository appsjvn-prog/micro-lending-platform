
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID

#  Login Request 
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

#  Token Response 
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: str

# Refresh Token Request 
class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Token Data (internal) 
class TokenData(BaseModel):
    user_id: Optional[str] = None
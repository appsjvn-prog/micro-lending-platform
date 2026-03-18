from sqlalchemy import Column, String, Enum, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from datetime import datetime

from app.core.database import Base
from app.core.timezone import utc_now



class AddressType(str, enum.Enum):
    HOME = "HOME"
    WORK = "WORK"
    PERMANENT = "PERMANENT"

class Address(Base):
    __tablename__ = "addresses"
    

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    
    # Address Type
    address_type = Column(Enum(AddressType), nullable=False, default=AddressType.HOME)
    is_primary = Column(Boolean, default=False, nullable=False)
    
    # Address Details
    address_line1 = Column(String(100), nullable=False)
    address_line2 = Column(String(100), nullable=True)
    landmark = Column(String(100), nullable=True)
    city = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    district = Column(String(50), nullable=True)
    pincode = Column(String(10), nullable=False)
    country = Column(String(50), nullable=False, default="India")
    
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user_profile = relationship("UserProfile", back_populates="addresses")
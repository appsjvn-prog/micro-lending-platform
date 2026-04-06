from sqlalchemy import Column, DateTime, UUID, ForeignKey
from app.core.timezone import utc_now

class AuditMixin:
    """Add audit fields to models - NO relationships here!"""
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
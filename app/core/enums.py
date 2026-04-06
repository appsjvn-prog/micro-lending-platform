from enum import Enum
from typing import Any, Optional

class CaseInsensitiveEnum(str, Enum):
    """Base class for case-insensitive string enums"""

    @classmethod
    def _missing_(cls, value: Any) -> Optional["CaseInsensitiveEnum"]:
        """Handle case-insensitive lookup"""
        if isinstance(value, str):
            value_upper = value.upper()
            for member in cls:
                if member.value == value_upper:
                    return member
        return super()._missing_(value)
    
    @classmethod
    def from_string(cls, value: str) -> Optional["CaseInsensitiveEnum"]:
        """Convert string to enum case-insensitively"""
        if not value:
            return None
        try:
            return cls(value.upper())
        except ValueError:
            return None
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if string is valid enum value (case-insensitive)"""
        return cls.from_string(value) is not None
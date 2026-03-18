from datetime import datetime, timezone
from typing import Optional

# Set your desired local timezone
LOCAL_TIMEZONE = timezone.utc  # Default to UTC
# For India: you'd need to use pytz or zoneinfo
# from zoneinfo import ZoneInfo
# LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")

def utc_now() -> datetime:
    """
    Get current UTC time (for database storage)
    Python 3.12+ compliant - no deprecation warning
    """
    return datetime.now(timezone.utc)

def local_now() -> datetime:
    """Get current local time (for display)"""
    return datetime.now(LOCAL_TIMEZONE)

def utc_to_local(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to local timezone"""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(LOCAL_TIMEZONE)

def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Format datetime with timezone"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(format)

def is_expired(expiry_time: datetime) -> bool:
    """Check if a datetime has expired (UTC comparison)"""
    if expiry_time.tzinfo is None:
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
    return expiry_time < utc_now()
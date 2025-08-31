"""
Centralized datetime utilities for consistent timezone handling.

This module provides timezone-aware datetime utilities to ensure consistent
handling of dates and times throughout the application.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


class TimezoneUtils:
    """Utility class for consistent timezone-aware datetime operations."""
    
    @staticmethod
    def utc_now() -> datetime:
        """
        Get current UTC time with timezone information.
        
        Returns:
            datetime: Current UTC time as timezone-aware datetime
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def from_timestamp(timestamp: float) -> datetime:
        """
        Convert Unix timestamp to timezone-aware UTC datetime.
        
        Args:
            timestamp: Unix timestamp (seconds since epoch)
            
        Returns:
            datetime: Timezone-aware datetime in UTC
        """
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    
    @staticmethod
    def ensure_utc(dt: datetime) -> datetime:
        """
        Ensure datetime is timezone-aware in UTC.
        
        If the datetime is naive, assume it's already in UTC.
        If it's timezone-aware, convert to UTC.
        
        Args:
            dt: DateTime object to convert
            
        Returns:
            datetime: Timezone-aware datetime in UTC
        """
        if dt.tzinfo is None:
            # Assume naive datetime is already UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    @staticmethod
    def to_timestamp(dt: datetime) -> float:
        """
        Convert datetime to Unix timestamp.
        
        Args:
            dt: DateTime object to convert
            
        Returns:
            float: Unix timestamp
        """
        # Ensure the datetime is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    
    @staticmethod
    def add_seconds(dt: datetime, seconds: int) -> datetime:
        """
        Add seconds to a datetime while preserving timezone info.
        
        Args:
            dt: Base datetime
            seconds: Seconds to add
            
        Returns:
            datetime: New datetime with added seconds
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt + timedelta(seconds=seconds)
    
    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        """
        Add days to a datetime while preserving timezone info.
        
        Args:
            dt: Base datetime
            days: Days to add
            
        Returns:
            datetime: New datetime with added days
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt + timedelta(days=days)


# Convenience functions for common operations
def utc_now() -> datetime:
    """Get current UTC time with timezone information."""
    return TimezoneUtils.utc_now()


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC."""
    return TimezoneUtils.ensure_utc(dt)


def from_timestamp(timestamp: float) -> datetime:
    """Convert Unix timestamp to timezone-aware UTC datetime."""
    return TimezoneUtils.from_timestamp(timestamp)
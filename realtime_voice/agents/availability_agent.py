"""
Availability Agent

Checks appointment availability based on service, date range, and optional staff.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import Any

from .database import fetch_all, get_schema


@dataclass
class AvailabilityRequest:
    """Request for checking availability."""
    service_id: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    staff_id: str | None = None


@dataclass
class AvailableSlot:
    """An available appointment slot."""
    slot_id: str
    service_id: str
    staff_id: str | None
    start_time: datetime
    end_time: datetime
    location: str | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "slot_id": self.slot_id,
            "service_id": self.service_id,
            "staff_id": self.staff_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
        }


class AvailabilityAgent:
    """
    Agent for checking appointment availability.
    
    Queries the database for available (unbooked) slots matching
    the requested criteria.
    """

    def __init__(self):
        self.schema = get_schema()

    def check_availability(
        self,
        service_id: str,
        start_date: str,
        end_date: str,
        staff_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Check for available appointment slots.
        
        Args:
            service_id: ID of the service to check.
            start_date: Start of date range (YYYY-MM-DD).
            end_date: End of date range (YYYY-MM-DD).
            staff_id: Optional staff ID to filter by.
            limit: Maximum number of results.
        
        Returns:
            List of available slots as dictionaries.
        """
        where_clauses = [
            "service_id = %s",
            "start_time >= %s",
            "end_time <= %s",
            "is_booked = FALSE",
        ]
        params: list[Any] = [service_id, start_date, end_date]
        
        if staff_id:
            where_clauses.append("staff_id = %s")
            params.append(staff_id)
        
        query = f"""
            SELECT 
                slot_id,
                service_id,
                staff_id,
                start_time,
                end_time,
                location
            FROM {self.schema}.appointment_slots
            WHERE {" AND ".join(where_clauses)}
            ORDER BY start_time
            LIMIT {limit}
        """
        
        return fetch_all(query, params)

    def get_services(self) -> list[dict[str, Any]]:
        """
        Get all available services.
        
        Returns:
            List of services with id, name, and description.
        """
        query = f"""
            SELECT service_id, service_name, description
            FROM {self.schema}.services
            ORDER BY service_name
        """
        return fetch_all(query)

    def resolve_service_id(self, service_name: str) -> str | None:
        """
        Resolve a service name to its ID.
        
        Args:
            service_name: Name of the service (case-insensitive).
        
        Returns:
            Service ID or None if not found.
        """
        query = f"""
            SELECT service_id
            FROM {self.schema}.services
            WHERE LOWER(service_name) = LOWER(%s)
            LIMIT 1
        """
        rows = fetch_all(query, [service_name])
        return rows[0]["service_id"] if rows else None

    def get_staff(self, service_id: str | None = None) -> list[dict[str, Any]]:
        """
        Get staff members, optionally filtered by service.
        
        Args:
            service_id: Optional service ID to filter by.
        
        Returns:
            List of staff members.
        """
        # For now, return all staff. Can be extended to filter by service.
        query = f"""
            SELECT staff_id, full_name, role
            FROM {self.schema}.staff
            ORDER BY full_name
        """
        return fetch_all(query)


# Standalone function for dispatcher compatibility
def check_availability(
    service_id: str,
    start_date: str,
    end_date: str,
    staff_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Check for available appointment slots.
    
    This is a standalone function wrapper for use with the agent dispatcher.
    
    Args:
        service_id: ID of the service to check.
        start_date: Start of date range (YYYY-MM-DD).
        end_date: End of date range (YYYY-MM-DD).
        staff_id: Optional staff ID to filter by.
    
    Returns:
        List of available slots.
    """
    agent = AvailabilityAgent()
    return agent.check_availability(
        service_id=service_id,
        start_date=start_date,
        end_date=end_date,
        staff_id=staff_id,
    )

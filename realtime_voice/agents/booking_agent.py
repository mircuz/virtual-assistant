"""
Booking Agent

Handles appointment booking operations including slot reservation
and customer appointment creation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .database import execute, get_schema


@dataclass
class BookingRequest:
    """Request for booking an appointment."""
    customer_id: str
    service_id: str
    slot_id: str
    staff_id: str | None = None
    notes: str | None = None


@dataclass
class BookingResult:
    """Result of a booking operation."""
    success: bool
    appointment_id: str | None = None
    message: str = ""
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "appointment_id": self.appointment_id,
            "message": self.message,
            "details": self.details,
        }


class BookingAgent:
    """
    Agent for booking appointments.
    
    Handles the complete booking flow:
    1. Validate slot availability
    2. Create appointment record
    3. Mark slot as booked
    """

    def __init__(self):
        self.schema = get_schema()

    def book_appointment(
        self,
        customer_id: str,
        service_id: str,
        slot_id: str,
        staff_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Book an appointment slot for a customer.
        
        Args:
            customer_id: ID of the customer making the booking.
            service_id: ID of the service being booked.
            slot_id: ID of the time slot to book.
            staff_id: Optional staff ID (uses slot's staff if not provided).
            notes: Optional booking notes.
        
        Returns:
            Dictionary with booking result including rows_affected.
        """
        # Build the WHERE clause
        where_clauses = [
            "s.slot_id = %s",
            "s.service_id = %s",
            "s.is_booked = FALSE",
        ]
        params: list[Any] = [customer_id, notes, slot_id, service_id]
        
        if staff_id:
            where_clauses.append("s.staff_id = %s")
            params.append(staff_id)
        
        # Insert the appointment
        query = f"""
            INSERT INTO {self.schema}.appointments
                (appointment_id, customer_id, service_id, slot_id, staff_id, 
                 start_time, end_time, status, notes)
            SELECT 
                gen_random_uuid(), 
                %s, 
                s.service_id, 
                s.slot_id, 
                s.staff_id, 
                s.start_time, 
                s.end_time, 
                'BOOKED', 
                %s
            FROM {self.schema}.appointment_slots s
            WHERE {" AND ".join(where_clauses)}
        """
        
        rows_affected = execute(query, params)
        
        # If booking succeeded, mark the slot as booked
        if rows_affected > 0:
            execute(
                f"UPDATE {self.schema}.appointment_slots SET is_booked = TRUE WHERE slot_id = %s",
                [slot_id],
            )
        
        return {"rows_affected": rows_affected}

# Standalone function for dispatcher compatibility
def book_appointment(
    customer_id: str,
    service_id: str,
    slot_id: str,
    staff_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Book an appointment slot for a customer.
    
    This is a standalone function wrapper for use with the agent dispatcher.
    
    Args:
        customer_id: ID of the customer making the booking.
        service_id: ID of the service being booked.
        slot_id: ID of the time slot to book.
        staff_id: Optional staff ID.
        notes: Optional booking notes.
    
    Returns:
        Dictionary with booking result.
    """
    agent = BookingAgent()
    return agent.book_appointment(
        customer_id=customer_id,
        service_id=service_id,
        slot_id=slot_id,
        staff_id=staff_id,
        notes=notes,
    )

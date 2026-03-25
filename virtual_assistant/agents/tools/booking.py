"""
Booking Tool

Creates appointments directly in the new appointments table.
Relies on PostgreSQL EXCLUDE constraints for double-booking prevention —
no manual lock/check needed.
"""

from __future__ import annotations

from typing import Any

from ..database import execute, fetch_all, get_schema
from ..base import BaseAgent


class BookingTool(BaseAgent):
    """
    Tool for booking appointments.

    Inserts directly into assistant_mochi.appointments.
    The DB EXCLUDE constraint on (staff_id, tstzrange) and (seat_id, tstzrange)
    guarantees no double-bookings at the database level.
    """

    @property
    def name(self) -> str:
        return "booking"

    def __init__(self) -> None:
        self._schema: str | None = None

    @property
    def schema(self) -> str:
        if self._schema is None:
            self._schema = get_schema()
        return self._schema

    def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Book an appointment.

        Required args: customer_id, service_id, staff_id, start_time (YYYY-MM-DD HH:MM)
        Optional args: seat_id, notes
        """
        customer_id = args.get("customer_id")
        service_id  = args.get("service_id")
        staff_id    = args.get("staff_id")
        start_time  = args.get("start_time")
        seat_id     = args.get("seat_id")
        notes       = args.get("notes")

        if not all([customer_id, service_id, staff_id, start_time]):
            return {
                "success": False,
                "rows_affected": 0,
                "error": "Missing required fields: customer_id, service_id, staff_id, start_time",
            }

        return self.book_appointment(
            customer_id=customer_id,
            service_id=service_id,
            staff_id=staff_id,
            start_time=start_time,
            seat_id=seat_id,
            notes=notes,
        )

    def book_appointment(
        self,
        customer_id: str,
        service_id: str,
        staff_id: str,
        start_time: str,
        seat_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Insert appointment; end_time is computed from service duration.

        The PostgreSQL EXCLUDE constraints will raise an error if the slot
        is already taken — we catch that and return a clear failure dict.
        """
        # Compute end_time = start_time + service duration
        query = f"""
            INSERT INTO {self.schema}.appointments
                (customer_id, staff_id, seat_id, service_id,
                 start_time, end_time, status, notes)
            SELECT
                %s::uuid,
                %s::uuid,
                %s::uuid,
                svc.id,
                %s::timestamptz,
                %s::timestamptz + (svc.duration_minutes || ' minutes')::INTERVAL,
                'scheduled',
                %s
            FROM {self.schema}.services svc
            WHERE svc.id = %s::uuid
              AND svc.is_active = TRUE
            RETURNING
                id::text AS appointment_id,
                start_time,
                end_time,
                status
        """
        params = [
            customer_id,
            staff_id,
            seat_id,        # NULL if not provided
            start_time,
            start_time,
            notes,
            service_id,
        ]

        try:
            rows = fetch_all(query, params)
            if not rows:
                return {
                    "success": False,
                    "rows_affected": 0,
                    "error": "Service not found or inactive.",
                }
            row = rows[0]
            return {
                "success": True,
                "rows_affected": 1,
                "appointment_id": row["appointment_id"],
                "start_time": str(row["start_time"]),
                "end_time":   str(row["end_time"]),
                "status":     row["status"],
            }
        except Exception as e:
            err = str(e)
            if "appointments_no_staff_overlap" in err:
                return {
                    "success": False,
                    "rows_affected": 0,
                    "error": "That time slot is already booked for this staff member.",
                }
            if "appointments_no_seat_overlap" in err:
                return {
                    "success": False,
                    "rows_affected": 0,
                    "error": "That seat is already occupied at the requested time.",
                }
            return {"success": False, "rows_affected": 0, "error": err}

    def cancel_appointment(
        self,
        appointment_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Cancel an existing appointment."""
        query = f"""
            UPDATE {self.schema}.appointments
            SET status = 'cancelled',
                cancelled_at = now(),
                cancellation_reason = %s
            WHERE id = %s::uuid
              AND status NOT IN ('cancelled', 'completed', 'no_show')
        """
        rows_affected = execute(query, [reason, appointment_id])
        return {"success": rows_affected > 0, "rows_affected": rows_affected}

    def get_customer_appointments(
        self,
        customer_id: str,
        upcoming_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Return a customer's appointments."""
        where = "WHERE a.customer_id = %s::uuid AND a.status NOT IN ('cancelled', 'no_show')"
        if upcoming_only:
            where += " AND a.start_time >= now()"
        query = f"""
            SELECT
                a.id::text AS appointment_id,
                a.start_time, a.end_time, a.status,
                svc.service_name, svc.price_eur,
                st.full_name AS staff_name,
                seat.seat_name
            FROM {self.schema}.appointments a
            JOIN {self.schema}.services svc ON svc.id = a.service_id
            JOIN {self.schema}.staff st ON st.id = a.staff_id
            LEFT JOIN {self.schema}.seats seat ON seat.id = a.seat_id
            {where}
            ORDER BY a.start_time
        """
        rows = fetch_all(query, [customer_id])
        for row in rows:
            for key in ("start_time", "end_time"):
                if key in row and row[key] is not None:
                    row[key] = str(row[key])
        return rows

"""
Availability Tool

Checks appointment availability using the available_slots() PostgreSQL function,
which accounts for staff schedules, existing bookings, seat types, and
staff–service capabilities.
"""

from __future__ import annotations

from typing import Any

from ..database import fetch_all, get_schema
from ..base import BaseAgent


class AvailabilityTool(BaseAgent):
    """
    Tool for checking appointment availability.

    Calls the assistant_mochi.available_slots() database function which
    returns free (staff, seat, service, time) combinations for a date range,
    respecting double-booking constraints and staff schedules.
    """

    @property
    def name(self) -> str:
        return "availability"

    def __init__(self) -> None:
        self._schema: str | None = None

    @property
    def schema(self) -> str:
        if self._schema is None:
            self._schema = get_schema()
        return self._schema

    def execute(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Check available appointment slots.

        Args:
            args: Dict with start_date, end_date (YYYY-MM-DD), and optionally
                  service_id, staff_id, service_name.

        Returns:
            List of available slot dicts with staff, seat, service, and time info.
        """
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        service_id = args.get("service_id")
        staff_id = args.get("staff_id")

        if not start_date or not end_date:
            return []

        # Resolve service name to ID if needed
        if not service_id and args.get("service_name"):
            service_id = self.resolve_service_id(args["service_name"])

        return self.check_availability(
            start_date=start_date,
            end_date=end_date,
            service_id=service_id,
            staff_id=staff_id,
        )

    def check_availability(
        self,
        start_date: str,
        end_date: str,
        service_id: str | None = None,
        staff_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Return available slots via the available_slots() DB function.

        Args:
            start_date: Start of search window (YYYY-MM-DD).
            end_date:   End of search window (YYYY-MM-DD).
            service_id: Optional UUID to filter by service.
            staff_id:   Optional UUID to filter by staff member.
            limit:      Max results to return (default 20).

        Returns:
            List of dicts: slot_start, slot_end, staff_id, staff_name,
                           seat_id, seat_name, service_id, service_name, duration_minutes.
        """
        # Build base query using the available_slots function
        # Cast date strings to timestamptz at start/end of business day
        base_query = f"""
            SELECT
                slot_start,
                slot_end,
                staff_id::text,
                staff_name,
                seat_id::text,
                seat_name,
                service_id::text,
                service_name,
                duration_minutes
            FROM {self.schema}.available_slots(
                %s::timestamptz,
                %s::timestamptz,
                %s::uuid
            )
        """
        params: list[Any] = [
            f"{start_date} 08:00:00+01",
            f"{end_date} 20:00:00+01",
            service_id,  # NULL is fine, function handles it
        ]

        # Optional staff filter applied after the function call
        if staff_id:
            base_query += " WHERE staff_id = %s::uuid"
            params.append(staff_id)

        base_query += f" LIMIT {limit}"

        rows = fetch_all(base_query, params)

        # Serialise timestamps for JSON
        for row in rows:
            for key in ("slot_start", "slot_end"):
                if key in row and row[key] is not None:
                    row[key] = str(row[key])

        return rows

    def get_services(self) -> list[dict[str, Any]]:
        """Return all active services with price and duration."""
        query = f"""
            SELECT
                id::text AS service_id,
                service_name,
                description,
                duration_minutes,
                price_eur,
                category
            FROM {self.schema}.services
            WHERE is_active = TRUE
            ORDER BY category, service_name
        """
        return fetch_all(query)

    def get_staff(self, service_id: str | None = None) -> list[dict[str, Any]]:
        """Return active staff, optionally filtered by service capability."""
        if service_id:
            query = f"""
                SELECT s.id::text AS staff_id, s.full_name, s.role
                FROM {self.schema}.staff s
                INNER JOIN {self.schema}.staff_services ss ON ss.staff_id = s.id
                WHERE s.is_active = TRUE
                  AND ss.service_id = %s::uuid
                ORDER BY s.full_name
            """
            return fetch_all(query, [service_id])

        query = f"""
            SELECT id::text AS staff_id, full_name, role
            FROM {self.schema}.staff
            WHERE is_active = TRUE
            ORDER BY full_name
        """
        return fetch_all(query)

    def resolve_service_id(self, service_name: str) -> str | None:
        """Resolve a service name (case-insensitive, partial match) to its UUID."""
        query = f"""
            SELECT id::text AS service_id
            FROM {self.schema}.services
            WHERE is_active = TRUE
              AND (
                LOWER(service_name) = LOWER(%s)
                OR LOWER(service_name) LIKE LOWER(%s)
              )
            LIMIT 1
        """
        rows = fetch_all(query, [service_name, f"%{service_name}%"])
        return rows[0]["service_id"] if rows else None

    # Alias kept for backward compatibility with engine.py
    AvailabilityAgent = None  # replaced by this class


# Backward-compat alias
AvailabilityAgent = AvailabilityTool

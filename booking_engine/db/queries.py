"""SQL query functions for all Booking Engine operations."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from psycopg_pool import AsyncConnectionPool

_ROME = ZoneInfo("Europe/Rome")


async def get_shop(pool: AsyncConnectionPool, shop_id: UUID) -> dict | None:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT * FROM shops WHERE id = %s AND is_active", (shop_id,)
        )
        return await cur.fetchone()


async def list_staff(pool: AsyncConnectionPool, shop_id: UUID) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, full_name, role, bio FROM staff "
            "WHERE shop_id = %s AND is_active ORDER BY full_name",
            (shop_id,),
        )
        return await cur.fetchall()


async def get_staff_services(pool: AsyncConnectionPool, staff_id: UUID) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT s.id, s.service_name, s.duration_minutes, s.price_eur, s.category "
            "FROM services s JOIN staff_services ss ON s.id = ss.service_id "
            "WHERE ss.staff_id = %s AND s.is_active ORDER BY s.service_name",
            (staff_id,),
        )
        return await cur.fetchall()


async def list_services(pool: AsyncConnectionPool, shop_id: UUID) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, service_name, description, duration_minutes, price_eur, category "
            "FROM services WHERE shop_id = %s AND is_active ORDER BY category, service_name",
            (shop_id,),
        )
        return await cur.fetchall()


async def find_customers_by_phone(pool: AsyncConnectionPool, shop_id: UUID, phone: str) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT c.id, c.full_name, c.preferred_staff_id, c.notes "
            "FROM customers c JOIN phone_contacts pc ON c.id = pc.customer_id "
            "WHERE c.shop_id = %s AND pc.phone_number = %s "
            "ORDER BY pc.last_seen_at DESC",
            (shop_id, phone),
        )
        return await cur.fetchall()


async def find_customers_by_name_and_phone(
    pool: AsyncConnectionPool, shop_id: UUID, name: str, phone: str
) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT c.id, c.full_name, c.preferred_staff_id, c.notes "
            "FROM customers c JOIN phone_contacts pc ON c.id = pc.customer_id "
            "WHERE c.shop_id = %s AND pc.phone_number = %s "
            "AND LOWER(c.full_name) LIKE LOWER(%s) || '%%' "
            "ORDER BY pc.last_seen_at DESC",
            (shop_id, phone, name),
        )
        return await cur.fetchall()


async def create_customer(
    pool: AsyncConnectionPool, shop_id: UUID, full_name: str,
    phone_number: str | None = None,
) -> dict:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO customers (shop_id, full_name) VALUES (%s, %s) RETURNING *",
            (shop_id, full_name),
        )
        customer = await cur.fetchone()
        if phone_number and customer:
            await conn.execute(
                "INSERT INTO phone_contacts (phone_number, customer_id) "
                "VALUES (%s, %s) ON CONFLICT (phone_number, customer_id) DO UPDATE "
                "SET last_seen_at = now()",
                (phone_number, customer["id"]),
            )
        return customer


async def upsert_phone_contact(pool: AsyncConnectionPool, phone: str, customer_id: UUID) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO phone_contacts (phone_number, customer_id) "
            "VALUES (%s, %s) ON CONFLICT (phone_number, customer_id) "
            "DO UPDATE SET last_seen_at = now()",
            (phone, customer_id),
        )


async def get_available_slots(
    pool: AsyncConnectionPool,
    shop_id: UUID,
    service_ids: list[UUID],
    start_date: date,
    end_date: date,
    staff_id: UUID | None = None,
) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT staff_id, staff_name, slot_start, slot_end "
            "FROM available_slots(%s, %s, %s, %s, %s)",
            (
                shop_id,
                datetime.combine(start_date, time(0, 0), tzinfo=_ROME),
                datetime.combine(end_date, time(23, 59), tzinfo=_ROME),
                service_ids,
                staff_id,
            ),
        )
        return await cur.fetchall()


async def create_appointment(
    pool: AsyncConnectionPool,
    shop_id: UUID,
    customer_id: UUID,
    staff_id: UUID,
    service_ids: list[UUID],
    start_time: datetime,
    notes: str | None = None,
) -> dict:
    async with pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "SELECT COALESCE(SUM(duration_minutes), 0) AS total, "
                "array_agg(json_build_object("
                "  'service_id', id, 'duration_minutes', duration_minutes, 'price_eur', price_eur"
                ")) AS details "
                "FROM services WHERE id = ANY(%s) AND is_active",
                (service_ids,),
            )
            row = await cur.fetchone()
            total_minutes = row["total"]
            end_time = start_time + timedelta(minutes=total_minutes)

            cur = await conn.execute(
                "INSERT INTO appointments "
                "(shop_id, customer_id, staff_id, start_time, end_time, status, notes) "
                "VALUES (%s, %s, %s, %s, %s, 'scheduled', %s) RETURNING *",
                (shop_id, customer_id, staff_id, start_time, end_time, notes),
            )
            appointment = await cur.fetchone()

            for sid in service_ids:
                await conn.execute(
                    "INSERT INTO appointment_services "
                    "(appointment_id, service_id, duration_minutes, price_eur) "
                    "SELECT %s, id, duration_minutes, price_eur "
                    "FROM services WHERE id = %s",
                    (appointment["id"], sid),
                )

            return appointment


async def list_appointments(
    pool: AsyncConnectionPool,
    shop_id: UUID,
    customer_id: UUID | None = None,
    status: str | None = None,
) -> list[dict]:
    async with pool.connection() as conn:
        conditions = ["a.shop_id = %s"]
        params: list = [shop_id]

        if customer_id:
            conditions.append("a.customer_id = %s")
            params.append(customer_id)
        if status:
            conditions.append("a.status = %s")
            params.append(status)

        where = " AND ".join(conditions)
        cur = await conn.execute(
            f"SELECT a.*, st.full_name AS staff_name "
            f"FROM appointments a JOIN staff st ON a.staff_id = st.id "
            f"WHERE {where} ORDER BY a.start_time",
            params,
        )
        rows = await cur.fetchall()

        for row in rows:
            svc_cur = await conn.execute(
                "SELECT aps.service_id, s.service_name, aps.duration_minutes, aps.price_eur "
                "FROM appointment_services aps JOIN services s ON aps.service_id = s.id "
                "WHERE aps.appointment_id = %s",
                (row["id"],),
            )
            row["services"] = await svc_cur.fetchall()

        return rows


async def cancel_appointment(
    pool: AsyncConnectionPool, shop_id: UUID, appointment_id: UUID
) -> dict | None:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE appointments SET status = 'cancelled' "
            "WHERE id = %s AND shop_id = %s AND status IN ('scheduled', 'confirmed') "
            "RETURNING *",
            (appointment_id, shop_id),
        )
        return await cur.fetchone()


async def reschedule_appointment(
    pool: AsyncConnectionPool,
    shop_id: UUID,
    appointment_id: UUID,
    new_start_time: datetime,
    new_staff_id: UUID | None = None,
) -> dict | None:
    async with pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "SELECT * FROM appointments "
                "WHERE id = %s AND shop_id = %s AND status IN ('scheduled', 'confirmed')",
                (appointment_id, shop_id),
            )
            current = await cur.fetchone()
            if not current:
                return None

            duration = current["end_time"] - current["start_time"]
            new_end = new_start_time + duration
            staff = new_staff_id or current["staff_id"]

            await conn.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = %s",
                (appointment_id,),
            )

            cur = await conn.execute(
                "INSERT INTO appointments "
                "(shop_id, customer_id, staff_id, start_time, end_time, status, notes) "
                "VALUES (%s, %s, %s, %s, %s, 'scheduled', %s) RETURNING *",
                (shop_id, current["customer_id"], staff, new_start_time, new_end, current["notes"]),
            )
            new_appt = await cur.fetchone()

            await conn.execute(
                "INSERT INTO appointment_services (appointment_id, service_id, duration_minutes, price_eur) "
                "SELECT %s, service_id, duration_minutes, price_eur "
                "FROM appointment_services WHERE appointment_id = %s",
                (new_appt["id"], appointment_id),
            )

            return new_appt

"""SQL query functions for all Booking Engine operations (Databricks SQL)."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from booking_engine.db.connection import execute, execute_one, execute_void, get_table

_ROME = ZoneInfo("Europe/Rome")


class SlotConflictError(Exception):
    """Raised when a booking would overlap an existing appointment."""


async def get_shop(shop_id: UUID) -> dict | None:
    t = get_table("shops")
    return await execute_one(
        f"SELECT * FROM {t} WHERE id = %(id)s AND is_active = true",
        {"id": str(shop_id)},
    )


async def list_staff(shop_id: UUID) -> list[dict]:
    t = get_table("staff")
    return await execute(
        f"SELECT id, full_name, role, bio FROM {t} "
        f"WHERE shop_id = %(shop_id)s AND is_active = true ORDER BY full_name",
        {"shop_id": str(shop_id)},
    )


async def get_staff_services(staff_id: UUID) -> list[dict]:
    ts = get_table("services")
    tss = get_table("staff_services")
    return await execute(
        f"SELECT s.id, s.service_name, s.duration_minutes, s.price_eur, s.category "
        f"FROM {ts} s JOIN {tss} ss ON s.id = ss.service_id "
        f"WHERE ss.staff_id = %(staff_id)s AND s.is_active = true ORDER BY s.service_name",
        {"staff_id": str(staff_id)},
    )


async def list_services(shop_id: UUID) -> list[dict]:
    t = get_table("services")
    return await execute(
        f"SELECT id, service_name, description, duration_minutes, price_eur, category "
        f"FROM {t} WHERE shop_id = %(shop_id)s AND is_active = true "
        f"ORDER BY category, service_name",
        {"shop_id": str(shop_id)},
    )


async def find_customers_by_phone(shop_id: UUID, phone: str) -> list[dict]:
    tc = get_table("customers")
    tp = get_table("phone_contacts")
    return await execute(
        f"SELECT c.id, c.full_name, c.preferred_staff_id, c.notes "
        f"FROM {tc} c JOIN {tp} pc ON c.id = pc.customer_id "
        f"WHERE c.shop_id = %(shop_id)s AND pc.phone_number = %(phone)s "
        f"ORDER BY pc.last_seen_at DESC",
        {"shop_id": str(shop_id), "phone": phone},
    )


async def find_customers_by_name_and_phone(
    shop_id: UUID, name: str, phone: str
) -> list[dict]:
    tc = get_table("customers")
    tp = get_table("phone_contacts")
    return await execute(
        f"SELECT c.id, c.full_name, c.preferred_staff_id, c.notes "
        f"FROM {tc} c JOIN {tp} pc ON c.id = pc.customer_id "
        f"WHERE c.shop_id = %(shop_id)s AND pc.phone_number = %(phone)s "
        f"AND LOWER(c.full_name) LIKE CONCAT(LOWER(%(name)s), '%%') "
        f"ORDER BY pc.last_seen_at DESC",
        {"shop_id": str(shop_id), "phone": phone, "name": name},
    )


async def create_customer(
    shop_id: UUID, full_name: str, phone_number: str | None = None,
) -> dict:
    t = get_table("customers")
    tp = get_table("phone_contacts")
    cid = str(uuid4())
    await execute_void(
        f"INSERT INTO {t} (id, shop_id, full_name, created_at) "
        f"VALUES (%(id)s, %(shop_id)s, %(name)s, current_timestamp())",
        {"id": cid, "shop_id": str(shop_id), "name": full_name},
    )
    customer = await execute_one(f"SELECT * FROM {t} WHERE id = %(id)s", {"id": cid})
    if phone_number and customer:
        existing = await execute_one(
            f"SELECT id FROM {tp} WHERE phone_number = %(phone)s AND customer_id = %(cid)s",
            {"phone": phone_number, "cid": cid},
        )
        if existing:
            await execute_void(
                f"UPDATE {tp} SET last_seen_at = current_timestamp() "
                f"WHERE phone_number = %(phone)s AND customer_id = %(cid)s",
                {"phone": phone_number, "cid": cid},
            )
        else:
            await execute_void(
                f"INSERT INTO {tp} (id, phone_number, customer_id, last_seen_at) "
                f"VALUES (%(id)s, %(phone)s, %(cid)s, current_timestamp())",
                {"id": str(uuid4()), "phone": phone_number, "cid": cid},
            )
    return customer


async def upsert_phone_contact(phone: str, customer_id: UUID) -> None:
    tp = get_table("phone_contacts")
    cid = str(customer_id)
    existing = await execute_one(
        f"SELECT id FROM {tp} WHERE phone_number = %(phone)s AND customer_id = %(cid)s",
        {"phone": phone, "cid": cid},
    )
    if existing:
        await execute_void(
            f"UPDATE {tp} SET last_seen_at = current_timestamp() "
            f"WHERE phone_number = %(phone)s AND customer_id = %(cid)s",
            {"phone": phone, "cid": cid},
        )
    else:
        await execute_void(
            f"INSERT INTO {tp} (id, phone_number, customer_id, last_seen_at) "
            f"VALUES (%(id)s, %(phone)s, %(cid)s, current_timestamp())",
            {"id": str(uuid4()), "phone": phone, "cid": cid},
        )


async def get_available_slots(
    shop_id: UUID,
    service_ids: list[UUID],
    start_date: date,
    end_date: date,
    staff_id: UUID | None = None,
) -> list[dict]:
    """Python implementation of the available_slots logic."""
    ts = get_table("services")
    tst = get_table("staff")
    tss = get_table("staff_services")
    tsch = get_table("staff_schedules")
    ta = get_table("appointments")

    sid_list = ", ".join(f"'{s}'" for s in service_ids)
    num_services = len(service_ids)

    # Get total duration
    svc_rows = await execute(
        f"SELECT SUM(duration_minutes) as total FROM {ts} "
        f"WHERE id IN ({sid_list}) AND is_active = true"
    )
    total_minutes = int(svc_rows[0]["total"]) if svc_rows and svc_rows[0]["total"] else 0
    if total_minutes == 0:
        return []

    # Find eligible staff (who can do ALL requested services)
    staff_filter = f"AND st.id = '{staff_id}'" if staff_id else ""
    eligible = await execute(
        f"SELECT st.id AS staff_id, st.full_name AS staff_name "
        f"FROM {tst} st "
        f"WHERE st.shop_id = %(shop_id)s AND st.is_active = true {staff_filter} "
        f"AND (SELECT COUNT(DISTINCT ss.service_id) FROM {tss} ss "
        f"     WHERE ss.staff_id = st.id AND ss.service_id IN ({sid_list})) = {num_services}",
        {"shop_id": str(shop_id)},
    )
    if not eligible:
        return []

    # Generate candidate slots per staff per day
    slots = []
    current = start_date
    while current <= end_date:
        dow = current.weekday()  # 0=Monday (matches our schema)
        for staff_row in eligible:
            sid = staff_row["staff_id"]
            sname = staff_row["staff_name"]
            # Get schedule for this day
            scheds = await execute(
                f"SELECT start_time, end_time FROM {tsch} "
                f"WHERE staff_id = %(sid)s AND day_of_week = %(dow)s",
                {"sid": sid, "dow": dow},
            )
            for sched in scheds:
                st_parts = str(sched["start_time"]).split(":")
                et_parts = str(sched["end_time"]).split(":")
                win_start = datetime.combine(current, time(int(st_parts[0]), int(st_parts[1])), tzinfo=_ROME)
                win_end = datetime.combine(current, time(int(et_parts[0]), int(et_parts[1])), tzinfo=_ROME)

                # Generate 30-min candidate slots
                slot_start = win_start
                while slot_start + timedelta(minutes=total_minutes) <= win_end:
                    slot_end = slot_start + timedelta(minutes=total_minutes)
                    slots.append({
                        "staff_id": sid, "staff_name": sname,
                        "slot_start": slot_start, "slot_end": slot_end,
                    })
                    slot_start += timedelta(minutes=30)
        current += timedelta(days=1)

    if not slots:
        return []

    # Filter out slots that overlap existing appointments
    staff_ids_str = ", ".join(f"'{s['staff_id']}'" for s in eligible)
    from_ts = datetime.combine(start_date, time(0, 0), tzinfo=_ROME).isoformat()
    to_ts = datetime.combine(end_date, time(23, 59), tzinfo=_ROME).isoformat()
    existing = await execute(
        f"SELECT staff_id, start_time, end_time FROM {ta} "
        f"WHERE staff_id IN ({staff_ids_str}) "
        f"AND status NOT IN ('cancelled', 'no_show') "
        f"AND start_time < %(to_ts)s AND end_time > %(from_ts)s",
        {"from_ts": from_ts, "to_ts": to_ts},
    )

    def overlaps(slot, appt):
        a_start = appt["start_time"] if isinstance(appt["start_time"], datetime) else datetime.fromisoformat(str(appt["start_time"]))
        a_end = appt["end_time"] if isinstance(appt["end_time"], datetime) else datetime.fromisoformat(str(appt["end_time"]))
        s_start = slot["slot_start"]
        s_end = slot["slot_end"]
        # Make naive for comparison if needed
        if a_start.tzinfo is None:
            a_start = a_start.replace(tzinfo=_ROME)
            a_end = a_end.replace(tzinfo=_ROME)
        return s_start < a_end and s_end > a_start

    available = []
    for slot in slots:
        blocked = any(
            slot["staff_id"] == appt["staff_id"] and overlaps(slot, appt)
            for appt in existing
        )
        if not blocked:
            available.append(slot)

    available.sort(key=lambda s: (s["slot_start"], s["staff_name"]))
    return available


async def create_appointment(
    shop_id: UUID,
    customer_id: UUID,
    staff_id: UUID,
    service_ids: list[UUID],
    start_time: datetime,
    notes: str | None = None,
) -> dict:
    ts = get_table("services")
    ta = get_table("appointments")
    tas = get_table("appointment_services")

    sid_list = ", ".join(f"'{s}'" for s in service_ids)
    svc_rows = await execute(
        f"SELECT id, duration_minutes, price_eur FROM {ts} "
        f"WHERE id IN ({sid_list}) AND is_active = true"
    )
    total_minutes = sum(r["duration_minutes"] for r in svc_rows)
    end_time = start_time + timedelta(minutes=total_minutes)

    # Check for overlapping appointments
    overlap = await execute(
        f"SELECT id FROM {ta} "
        f"WHERE staff_id = %(staff_id)s AND status NOT IN ('cancelled', 'no_show') "
        f"AND start_time < %(end)s AND end_time > %(start)s",
        {"staff_id": str(staff_id), "start": start_time.isoformat(), "end": end_time.isoformat()},
    )
    if overlap:
        raise SlotConflictError("Time slot conflicts with existing appointment")

    appt_id = str(uuid4())
    await execute_void(
        f"INSERT INTO {ta} (id, shop_id, customer_id, staff_id, start_time, end_time, status, notes, created_at) "
        f"VALUES (%(id)s, %(shop_id)s, %(cid)s, %(sid)s, %(start)s, %(end)s, 'scheduled', %(notes)s, current_timestamp())",
        {
            "id": appt_id, "shop_id": str(shop_id), "cid": str(customer_id),
            "sid": str(staff_id), "start": start_time.isoformat(),
            "end": end_time.isoformat(), "notes": notes,
        },
    )

    for svc in svc_rows:
        await execute_void(
            f"INSERT INTO {tas} (appointment_id, service_id, duration_minutes, price_eur) "
            f"VALUES (%(aid)s, %(sid)s, %(dur)s, %(price)s)",
            {"aid": appt_id, "sid": svc["id"], "dur": svc["duration_minutes"], "price": float(svc["price_eur"]) if svc["price_eur"] else None},
        )

    return await execute_one(f"SELECT * FROM {ta} WHERE id = %(id)s", {"id": appt_id})


async def list_appointments(
    shop_id: UUID,
    customer_id: UUID | None = None,
    status: str | None = None,
) -> list[dict]:
    ta = get_table("appointments")
    tst = get_table("staff")
    tas = get_table("appointment_services")
    ts = get_table("services")

    conditions = ["a.shop_id = %(shop_id)s"]
    params = {"shop_id": str(shop_id)}

    if customer_id:
        conditions.append("a.customer_id = %(cid)s")
        params["cid"] = str(customer_id)
    if status:
        conditions.append("a.status = %(status)s")
        params["status"] = status

    where = " AND ".join(conditions)
    rows = await execute(
        f"SELECT a.*, st.full_name AS staff_name "
        f"FROM {ta} a JOIN {tst} st ON a.staff_id = st.id "
        f"WHERE {where} ORDER BY a.start_time",
        params,
    )

    for row in rows:
        svcs = await execute(
            f"SELECT aps.service_id, s.service_name, aps.duration_minutes, aps.price_eur "
            f"FROM {tas} aps JOIN {ts} s ON aps.service_id = s.id "
            f"WHERE aps.appointment_id = %(aid)s",
            {"aid": row["id"]},
        )
        row["services"] = svcs

    return rows


async def cancel_appointment(shop_id: UUID, appointment_id: UUID) -> dict | None:
    ta = get_table("appointments")
    aid = str(appointment_id)
    sid = str(shop_id)
    existing = await execute_one(
        f"SELECT * FROM {ta} WHERE id = %(aid)s AND shop_id = %(sid)s AND status IN ('scheduled', 'confirmed')",
        {"aid": aid, "sid": sid},
    )
    if not existing:
        return None
    await execute_void(
        f"UPDATE {ta} SET status = 'cancelled' WHERE id = %(aid)s",
        {"aid": aid},
    )
    return await execute_one(f"SELECT * FROM {ta} WHERE id = %(aid)s", {"aid": aid})


async def reschedule_appointment(
    shop_id: UUID,
    appointment_id: UUID,
    new_start_time: datetime,
    new_staff_id: UUID | None = None,
) -> dict | None:
    ta = get_table("appointments")
    tas = get_table("appointment_services")
    aid = str(appointment_id)
    sid = str(shop_id)

    current = await execute_one(
        f"SELECT * FROM {ta} WHERE id = %(aid)s AND shop_id = %(sid)s AND status IN ('scheduled', 'confirmed')",
        {"aid": aid, "sid": sid},
    )
    if not current:
        return None

    c_start = current["start_time"]
    c_end = current["end_time"]
    if isinstance(c_start, str):
        c_start = datetime.fromisoformat(c_start)
        c_end = datetime.fromisoformat(c_end)
    duration = c_end - c_start
    new_end = new_start_time + duration
    staff = str(new_staff_id) if new_staff_id else current["staff_id"]

    # Cancel old
    await execute_void(f"UPDATE {ta} SET status = 'cancelled' WHERE id = %(aid)s", {"aid": aid})

    # Create new
    new_id = str(uuid4())
    await execute_void(
        f"INSERT INTO {ta} (id, shop_id, customer_id, staff_id, start_time, end_time, status, notes, created_at) "
        f"VALUES (%(id)s, %(sid)s, %(cid)s, %(staff)s, %(start)s, %(end)s, 'scheduled', %(notes)s, current_timestamp())",
        {
            "id": new_id, "sid": sid, "cid": current["customer_id"],
            "staff": staff, "start": new_start_time.isoformat(),
            "end": new_end.isoformat(), "notes": current.get("notes"),
        },
    )

    # Copy services
    old_svcs = await execute(
        f"SELECT service_id, duration_minutes, price_eur FROM {tas} WHERE appointment_id = %(aid)s",
        {"aid": aid},
    )
    for svc in old_svcs:
        await execute_void(
            f"INSERT INTO {tas} (appointment_id, service_id, duration_minutes, price_eur) "
            f"VALUES (%(nid)s, %(sid)s, %(dur)s, %(price)s)",
            {"nid": new_id, "sid": svc["service_id"], "dur": svc["duration_minutes"],
             "price": float(svc["price_eur"]) if svc["price_eur"] else None},
        )

    return await execute_one(f"SELECT * FROM {ta} WHERE id = %(id)s", {"id": new_id})

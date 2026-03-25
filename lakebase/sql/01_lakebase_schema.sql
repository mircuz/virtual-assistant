-- =============================================================================
-- Italian Hair Salon Booking System - Production Schema
-- Schema: assistant_mochi
-- =============================================================================
-- Prevents double-booking of staff and seats, enforces staff-service capabilities,
-- tracks cancellations/no-shows, supports customer preferences.
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS btree_gist;    -- EXCLUDE on (uuid, tstzrange)

CREATE SCHEMA IF NOT EXISTS assistant_mochi;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Customers
CREATE TABLE IF NOT EXISTS assistant_mochi.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    phone_number TEXT,
    email TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'it',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE assistant_mochi.customers IS 'Salon customers; preferred_language for notifications (e.g. it, en)';
COMMENT ON COLUMN assistant_mochi.customers.preferred_language IS 'ISO 639-1 code for preferred language';

-- Staff (parrucchieri, stilisti, coloristi, assistenti)
CREATE TABLE IF NOT EXISTS assistant_mochi.staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    phone_number TEXT,
    email TEXT,
    bio TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE assistant_mochi.staff IS 'Salon staff with roles: stilista, colorista, assistente, etc.';
COMMENT ON COLUMN assistant_mochi.staff.role IS 'Role: stilista, colorista, assistente, etc.';

-- Physical seats (postazioni)
CREATE TABLE IF NOT EXISTS assistant_mochi.seats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seat_name TEXT NOT NULL,
    seat_type TEXT NOT NULL DEFAULT 'standard',
    is_active BOOLEAN NOT NULL DEFAULT true
);

COMMENT ON TABLE assistant_mochi.seats IS 'Physical chairs/postazioni; seat_type: standard, vip, wash';
COMMENT ON COLUMN assistant_mochi.seats.seat_type IS 'standard | vip | wash (for shampoo basin)';

-- Customer preferences (added after staff/seats exist)
ALTER TABLE assistant_mochi.customers
    ADD COLUMN IF NOT EXISTS preferred_staff_id UUID REFERENCES assistant_mochi.staff(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS preferred_seat_id UUID REFERENCES assistant_mochi.seats(id) ON DELETE SET NULL;

COMMENT ON COLUMN assistant_mochi.customers.preferred_staff_id IS 'Optional preferred stylist';
COMMENT ON COLUMN assistant_mochi.customers.preferred_seat_id IS 'Optional preferred seat/postazione';

-- Services (taglio, colore, trattamento, piega)
CREATE TABLE IF NOT EXISTS assistant_mochi.services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name TEXT NOT NULL,
    description TEXT,
    duration_minutes INT NOT NULL CHECK (duration_minutes > 0),
    price_eur NUMERIC(10,2) NOT NULL CHECK (price_eur >= 0),
    category TEXT NOT NULL,
    requires_seat_type TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true
);

COMMENT ON TABLE assistant_mochi.services IS 'Services offered; requires_seat_type e.g. wash for shampoo';
COMMENT ON COLUMN assistant_mochi.services.category IS 'taglio | colore | trattamento | piega';
COMMENT ON COLUMN assistant_mochi.services.requires_seat_type IS 'If set, service must be done at a seat of this type (e.g. wash)';

-- Staff-service mapping: which staff can perform which service
CREATE TABLE IF NOT EXISTS assistant_mochi.staff_services (
    staff_id UUID NOT NULL REFERENCES assistant_mochi.staff(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES assistant_mochi.services(id) ON DELETE CASCADE,
    PRIMARY KEY (staff_id, service_id)
);

COMMENT ON TABLE assistant_mochi.staff_services IS 'Many-to-many: staff capabilities (e.g. only senior coloristi do coloring)';

CREATE INDEX IF NOT EXISTS idx_staff_services_service_id
    ON assistant_mochi.staff_services(service_id);

-- Recurring weekly schedule per staff
CREATE TABLE IF NOT EXISTS assistant_mochi.staff_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES assistant_mochi.staff(id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    CHECK (end_time > start_time)
);

COMMENT ON TABLE assistant_mochi.staff_schedules IS 'Recurring weekly availability; day_of_week 0=Mon..6=Sun';
COMMENT ON COLUMN assistant_mochi.staff_schedules.day_of_week IS '0=Monday, 6=Sunday (ISO)';

CREATE INDEX IF NOT EXISTS idx_staff_schedules_staff_day
    ON assistant_mochi.staff_schedules(staff_id, day_of_week);

-- Appointments (bookings)
CREATE TABLE IF NOT EXISTS assistant_mochi.appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES assistant_mochi.customers(id) ON DELETE RESTRICT,
    staff_id UUID NOT NULL REFERENCES assistant_mochi.staff(id) ON DELETE RESTRICT,
    seat_id UUID REFERENCES assistant_mochi.seats(id) ON DELETE SET NULL,
    service_id UUID NOT NULL REFERENCES assistant_mochi.services(id) ON DELETE RESTRICT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show')),
    notes TEXT,
    booked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    CHECK (end_time > start_time)
);

COMMENT ON TABLE assistant_mochi.appointments IS 'Bookings; seat_id nullable for flexibility (e.g. walk-in)';
COMMENT ON COLUMN assistant_mochi.appointments.status IS 'scheduled | confirmed | completed | cancelled | no_show';

-- No double-booking of staff (exclude overlapping appointments for same staff)
ALTER TABLE assistant_mochi.appointments DROP CONSTRAINT IF EXISTS appointments_no_staff_overlap;
ALTER TABLE assistant_mochi.appointments
    ADD CONSTRAINT appointments_no_staff_overlap
    EXCLUDE USING gist (staff_id WITH =, tstzrange(start_time, end_time) WITH &&)
    WHERE (status NOT IN ('cancelled', 'no_show'));

-- No double-booking of seat (exclude overlapping appointments for same seat, when assigned)
ALTER TABLE assistant_mochi.appointments DROP CONSTRAINT IF EXISTS appointments_no_seat_overlap;
ALTER TABLE assistant_mochi.appointments
    ADD CONSTRAINT appointments_no_seat_overlap
    EXCLUDE USING gist (seat_id WITH =, tstzrange(start_time, end_time) WITH &&)
    WHERE (status NOT IN ('cancelled', 'no_show') AND seat_id IS NOT NULL);

-- Appointment indexes
CREATE INDEX IF NOT EXISTS idx_appointments_staff_start
    ON assistant_mochi.appointments(staff_id, start_time);

CREATE INDEX IF NOT EXISTS idx_appointments_seat_start
    ON assistant_mochi.appointments(seat_id, start_time)
    WHERE seat_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_appointments_customer_id
    ON assistant_mochi.appointments(customer_id);

CREATE INDEX IF NOT EXISTS idx_appointments_status_start
    ON assistant_mochi.appointments(status, start_time);

-- =============================================================================
-- HELPER FUNCTION: Available Slots
-- =============================================================================
-- Returns available (staff, seat, service, slot_start) combinations for a
-- given date range. Uses configurable slot granularity. Checks staff schedule
-- and existing appointments. Appointment window = slot_start + service duration.

CREATE OR REPLACE FUNCTION assistant_mochi.available_slots(
    p_from TIMESTAMPTZ,
    p_to TIMESTAMPTZ,
    p_service_id UUID DEFAULT NULL,
    p_slot_minutes INT DEFAULT 30
)
RETURNS TABLE (
    slot_start TIMESTAMPTZ,
    slot_end TIMESTAMPTZ,
    staff_id UUID,
    staff_name TEXT,
    seat_id UUID,
    seat_name TEXT,
    service_id UUID,
    service_name TEXT,
    duration_minutes INT
) AS $$
BEGIN
    RETURN QUERY
    WITH slot_times AS (
        SELECT
            ts AS slot_start,
            ts + (p_slot_minutes || ' minutes')::INTERVAL AS slot_end
        FROM generate_series(
            date_trunc('hour', p_from),
            p_to - (p_slot_minutes || ' minutes')::INTERVAL,
            (p_slot_minutes || ' minutes')::INTERVAL
        ) AS ts
    ),
    services_filtered AS (
        SELECT sv.*
        FROM assistant_mochi.services sv
        WHERE sv.is_active
          AND (p_service_id IS NULL OR sv.id = p_service_id)
    ),
    staff_candidates AS (
        SELECT
            st.slot_start,
            st.slot_end,
            s.id AS staff_id,
            s.full_name AS staff_name,
            srv.id AS service_id,
            srv.service_name,
            srv.duration_minutes,
            srv.requires_seat_type,
            (st.slot_start + (srv.duration_minutes || ' minutes')::INTERVAL) AS appt_end
        FROM slot_times st
        CROSS JOIN services_filtered srv
        INNER JOIN assistant_mochi.staff_services sts
            ON sts.service_id = srv.id
        INNER JOIN assistant_mochi.staff s
            ON s.id = sts.staff_id AND s.is_active
        INNER JOIN assistant_mochi.staff_schedules ss
            ON ss.staff_id = s.id
            AND ss.day_of_week = (EXTRACT(ISODOW FROM st.slot_start AT TIME ZONE 'Europe/Rome')::INT - 1)
            AND (st.slot_start AT TIME ZONE 'Europe/Rome')::TIME >= ss.start_time
            AND ((st.slot_start + (srv.duration_minutes || ' minutes')::INTERVAL) AT TIME ZONE 'Europe/Rome')::TIME <= ss.end_time
        WHERE st.slot_start + (srv.duration_minutes || ' minutes')::INTERVAL <= p_to
    ),
    staff_free AS (
        SELECT sc.*
        FROM staff_candidates sc
        WHERE NOT EXISTS (
            SELECT 1
            FROM assistant_mochi.appointments a
            WHERE a.staff_id = sc.staff_id
              AND a.status NOT IN ('cancelled', 'no_show')
              AND tstzrange(a.start_time, a.end_time) && tstzrange(sc.slot_start, sc.appt_end)
        )
    )
    SELECT
        sf.slot_start,
        sf.slot_end,
        sf.staff_id,
        sf.staff_name,
        seat.id AS seat_id,
        seat.seat_name,
        sf.service_id,
        sf.service_name,
        sf.duration_minutes
    FROM staff_free sf
    INNER JOIN assistant_mochi.seats seat
        ON seat.is_active
        AND (sf.requires_seat_type IS NULL OR seat.seat_type = sf.requires_seat_type)
        AND NOT EXISTS (
            SELECT 1
            FROM assistant_mochi.appointments a
            WHERE a.seat_id = seat.id
              AND a.status NOT IN ('cancelled', 'no_show')
              AND tstzrange(a.start_time, a.end_time) && tstzrange(sf.slot_start, sf.appt_end)
        )
    ORDER BY sf.slot_start, sf.staff_name, sf.service_name;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION assistant_mochi.available_slots IS 'Returns available (staff, seat, service) combinations. Usage: SELECT * FROM assistant_mochi.available_slots(''2025-03-10 09:00''::timestamptz, ''2025-03-10 18:00''::timestamptz);';

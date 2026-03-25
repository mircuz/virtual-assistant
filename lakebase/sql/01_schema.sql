-- Hair Salon Voice Assistant — Lakebase Schema
-- Schema: hair_salon (replaces old assistant_mochi)
-- Timezone: all TIMESTAMPTZ stored as UTC, displayed in Europe/Rome
-- Day-of-week: 0=Monday .. 6=Sunday (ISO)

CREATE SCHEMA IF NOT EXISTS hair_salon;
SET search_path TO hair_salon;

-- Enable btree_gist for EXCLUDE constraints
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS shops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    phone_number TEXT,
    address TEXT,
    welcome_message TEXT,
    tone_instructions TEXT,
    personality TEXT,
    special_instructions TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    role TEXT,
    phone_number TEXT,
    email TEXT,
    bio TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_staff_shop ON staff(shop_id) WHERE is_active;

CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    service_name TEXT NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    price_eur DECIMAL(8,2),
    category TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_services_shop ON services(shop_id) WHERE is_active;

CREATE TABLE IF NOT EXISTS staff_services (
    staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    PRIMARY KEY (staff_id, service_id)
);
CREATE INDEX idx_staff_services_service ON staff_services(service_id);

CREATE TABLE IF NOT EXISTS staff_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    CHECK (end_time > start_time),
    UNIQUE (staff_id, day_of_week)
);
CREATE INDEX idx_staff_schedules_staff ON staff_schedules(staff_id, day_of_week);

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT,
    preferred_staff_id UUID REFERENCES staff(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_customers_shop ON customers(shop_id);

CREATE TABLE IF NOT EXISTS phone_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (phone_number, customer_id)
);
CREATE INDEX idx_phone_contacts_phone ON phone_contacts(phone_number);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- no_show excluded from overlap check: a no-show should not block future bookings
    EXCLUDE USING gist (
        staff_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'no_show'))
);
CREATE INDEX idx_appointments_shop ON appointments(shop_id, start_time);
CREATE INDEX idx_appointments_staff ON appointments(staff_id, start_time);
CREATE INDEX idx_appointments_customer ON appointments(customer_id);
CREATE INDEX idx_appointments_status ON appointments(status, start_time);

CREATE TABLE IF NOT EXISTS appointment_services (
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    duration_minutes INTEGER NOT NULL,
    price_eur DECIMAL(8,2),
    PRIMARY KEY (appointment_id, service_id)
);

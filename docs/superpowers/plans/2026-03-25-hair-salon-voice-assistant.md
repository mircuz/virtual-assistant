# Hair Salon Voice Booking Assistant — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-service voice booking assistant for hair salons — a Booking Engine (REST API) and Voice Gateway (conversation + audio) — backed by Databricks Lakebase, with Italian language support and per-shop branding.

**Architecture:** Two independent FastAPI services. The Booking Engine owns all business logic (availability, booking, customers) and talks directly to Lakebase (PostgreSQL). The Voice Gateway handles conversation flow, LLM-based intent routing, response generation, STT/TTS, and calls the Booking Engine over HTTP. Both deploy as Databricks Apps.

**Tech Stack:** Python 3.11+, FastAPI, psycopg (v3 async), httpx, Pydantic v2, Databricks Model Serving (Llama 3.1 8B + Llama 3.3 70B), Whisper STT, Kokoro TTS, pytest, Lakebase (PostgreSQL)

**Spec:** `docs/superpowers/specs/2026-03-25-hair-salon-voice-assistant-design.md`

---

## File Map

### Files to Delete (Task 1)
- `realtime_voice/` — entire directory
- `personaplex_based/` — entire directory
- `.cursor/` — entire directory
- `virtual_assistant/` — entire directory
- `app/` — empty directory
- `.databricks/` — old sync config

### Lakebase SQL (Task 2)
- Create: `lakebase/sql/01_schema.sql` (replaces old)
- Create: `lakebase/sql/02_seed_data.sql` (replaces old)
- Create: `lakebase/sql/03_functions.sql` (new — `available_slots()`)

### Booking Engine (Tasks 3–8)
- Create: `booking_engine/__init__.py`
- Create: `booking_engine/config.py` — Pydantic Settings from env vars
- Create: `booking_engine/db/__init__.py`
- Create: `booking_engine/db/connection.py` — async psycopg pool
- Create: `booking_engine/db/queries.py` — SQL query functions (shops, customers, services, staff, availability, appointments)
- Create: `booking_engine/api/__init__.py`
- Create: `booking_engine/api/app.py` — FastAPI app with lifespan
- Create: `booking_engine/api/models.py` — Pydantic request/response models + error schema
- Create: `booking_engine/api/routes/__init__.py`
- Create: `booking_engine/api/routes/shops.py`
- Create: `booking_engine/api/routes/customers.py`
- Create: `booking_engine/api/routes/services.py`
- Create: `booking_engine/api/routes/availability.py`
- Create: `booking_engine/api/routes/appointments.py`

### Voice Gateway (Tasks 9–14)
- Create: `voice_gateway/__init__.py`
- Create: `voice_gateway/config.py` — Pydantic Settings
- Create: `voice_gateway/clients/__init__.py`
- Create: `voice_gateway/clients/booking_client.py` — async httpx client
- Create: `voice_gateway/conversation/__init__.py`
- Create: `voice_gateway/conversation/session.py` — session state + manager
- Create: `voice_gateway/conversation/prompt_assembler.py` — per-shop prompt building
- Create: `voice_gateway/conversation/intent_router.py` — small LLM intent extraction + guardrails
- Create: `voice_gateway/conversation/response_composer.py` — large LLM response generation
- Create: `voice_gateway/voice/__init__.py`
- Create: `voice_gateway/voice/stt.py` — Whisper endpoint client
- Create: `voice_gateway/voice/tts.py` — Kokoro endpoint client
- Create: `voice_gateway/api/__init__.py`
- Create: `voice_gateway/api/app.py` — FastAPI app
- Create: `voice_gateway/api/models.py` — Pydantic models
- Create: `voice_gateway/api/routes/__init__.py`
- Create: `voice_gateway/api/routes/conversations.py` — start, turn, end
- Create: `voice_gateway/api/routes/ws.py` — WebSocket scaffold

### Tests (throughout)
- Create: `tests/__init__.py`
- Create: `tests/conftest.py` — shared fixtures
- Create: `tests/booking_engine/__init__.py`
- Create: `tests/booking_engine/test_models.py`
- Create: `tests/booking_engine/test_queries.py`
- Create: `tests/booking_engine/test_routes_shops.py`
- Create: `tests/booking_engine/test_routes_customers.py`
- Create: `tests/booking_engine/test_routes_services.py`
- Create: `tests/booking_engine/test_routes_availability.py`
- Create: `tests/booking_engine/test_routes_appointments.py`
- Create: `tests/voice_gateway/__init__.py`
- Create: `tests/voice_gateway/test_session.py`
- Create: `tests/voice_gateway/test_prompt_assembler.py`
- Create: `tests/voice_gateway/test_intent_router.py`
- Create: `tests/voice_gateway/test_response_composer.py`
- Create: `tests/voice_gateway/test_booking_client.py`
- Create: `tests/voice_gateway/test_routes_conversations.py`

### Root files
- Modify: `requirements.txt`
- Create: `booking_engine/app.yaml` — Databricks App config
- Create: `voice_gateway/app.yaml` — Databricks App config

---

## Task 1: Cleanup — Delete Legacy Files & Update Dependencies

**Files:**
- Delete: `realtime_voice/`, `personaplex_based/`, `.cursor/`, `virtual_assistant/`, `app/`, `.databricks/`
- Modify: `requirements.txt`
- Create: `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Delete legacy directories**

```bash
rm -rf realtime_voice/ personaplex_based/ .cursor/ virtual_assistant/ app/ .databricks/
```

- [ ] **Step 2: Update requirements.txt**

Replace entire contents:

```
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Database (async)
psycopg[binary]>=3.2.0
psycopg-pool>=3.2.0

# HTTP client
httpx>=0.27.0

# Databricks
databricks-sdk>=0.81.0

# Voice
soundfile>=0.12.0
numpy>=1.24.0

# Test UI
gradio>=4.0.0

# Utilities
python-multipart>=0.0.9

# Testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-httpx>=0.30.0
```

- [ ] **Step 3: Create test scaffolding**

Create `tests/__init__.py` (empty) and `tests/conftest.py`:

```python
"""Shared test fixtures for booking engine and voice gateway."""
```

Create `tests/booking_engine/__init__.py` and `tests/voice_gateway/__init__.py` (both empty).

- [ ] **Step 4: Verify clean state**

```bash
ls -la
# Expected: docs/ lakebase/ tests/ requirements.txt README.md .gitignore .vscode/
# NO: realtime_voice/ personaplex_based/ .cursor/ virtual_assistant/ app/ .databricks/
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove legacy code and update dependencies for two-service architecture"
```

---

## Task 2: Lakebase Schema, Seed Data & Functions

**Files:**
- Create: `lakebase/sql/01_schema.sql`
- Create: `lakebase/sql/02_seed_data.sql`
- Create: `lakebase/sql/03_functions.sql`

- [ ] **Step 1: Write the schema SQL**

Create `lakebase/sql/01_schema.sql`:

```sql
-- Hair Salon Voice Assistant — Lakebase Schema
-- Schema: hair_salon (replaces old assistant_mochi)
-- Timezone: all TIMESTAMPTZ stored as UTC, displayed in Europe/Rome
-- Day-of-week: 0=Monday .. 6=Sunday (ISO)

CREATE SCHEMA IF NOT EXISTS hair_salon;
SET search_path TO hair_salon;

-- Enable btree_gist for EXCLUDE constraints
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ============================================================
-- SHOPS
-- ============================================================
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

-- ============================================================
-- STAFF
-- ============================================================
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

-- ============================================================
-- SERVICES
-- ============================================================
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

-- ============================================================
-- STAFF_SERVICES (M2M)
-- ============================================================
CREATE TABLE IF NOT EXISTS staff_services (
    staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    PRIMARY KEY (staff_id, service_id)
);

CREATE INDEX idx_staff_services_service ON staff_services(service_id);

-- ============================================================
-- STAFF_SCHEDULES
-- ============================================================
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

-- ============================================================
-- CUSTOMERS
-- ============================================================
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

-- ============================================================
-- PHONE_CONTACTS (soft link for caller ID)
-- ============================================================
CREATE TABLE IF NOT EXISTS phone_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (phone_number, customer_id)
);

CREATE INDEX idx_phone_contacts_phone ON phone_contacts(phone_number);

-- ============================================================
-- APPOINTMENTS
-- ============================================================
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
    -- Note: no_show excluded from overlap check (deviation from initial spec)
    -- Rationale: a no-show should not block future bookings at the same timeslot
    EXCLUDE USING gist (
        staff_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'no_show'))
);

CREATE INDEX idx_appointments_shop ON appointments(shop_id, start_time);
CREATE INDEX idx_appointments_staff ON appointments(staff_id, start_time);
CREATE INDEX idx_appointments_customer ON appointments(customer_id);
CREATE INDEX idx_appointments_status ON appointments(status, start_time);

-- ============================================================
-- APPOINTMENT_SERVICES (junction)
-- ============================================================
CREATE TABLE IF NOT EXISTS appointment_services (
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    duration_minutes INTEGER NOT NULL,
    price_eur DECIMAL(8,2),
    PRIMARY KEY (appointment_id, service_id)
);
```

- [ ] **Step 2: Write seed data**

Create `lakebase/sql/02_seed_data.sql`:

```sql
-- Seed data: Two shops for testing
SET search_path TO hair_salon;

-- ============================================================
-- SHOP A: Salon Bella (Milano)
-- ============================================================
INSERT INTO shops (id, name, phone_number, address, welcome_message, tone_instructions, personality, special_instructions) VALUES
('a0000000-0000-0000-0000-000000000001'::uuid, 'Salon Bella', '+39 02 1234567', 'Via Roma 42, Milano',
 'Ciao, benvenuto da Salon Bella! Come ti chiami?',
 'Amichevole e informale, dai del tu al cliente',
 'Sei Bella, l''assistente virtuale del Salon Bella. Sei solare, cordiale e sempre pronta ad aiutare.',
 'Se il cliente chiede di un servizio che non offriamo, suggerisci il servizio più simile disponibile.');

-- ============================================================
-- SHOP B: Studio Hair (Roma)
-- ============================================================
INSERT INTO shops (id, name, phone_number, address, welcome_message, tone_instructions, personality, special_instructions) VALUES
('b0000000-0000-0000-0000-000000000002'::uuid, 'Studio Hair', '+39 06 7654321', 'Via del Corso 15, Roma',
 'Buongiorno, benvenuto allo Studio Hair. Come posso aiutarla?',
 'Professionale e formale, dia del lei al cliente',
 'Sei l''assistente dello Studio Hair. Sei professionale, preciso e attento ai dettagli.',
 NULL);

-- ============================================================
-- STAFF — Shop A
-- ============================================================
INSERT INTO staff (id, shop_id, full_name, role, bio) VALUES
('11111111-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Mirco Meazzo', 'stilista senior', 'Stilista con 15 anni di esperienza, specializzato in tagli moderni'),
('11111111-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Giulia Verdi', 'colorista', 'Esperta di colorazioni e trattamenti'),
('11111111-0000-0000-0000-000000000003'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Marco Bianchi', 'stilista', 'Specializzato in tagli classici e barba');

-- STAFF — Shop B
INSERT INTO staff (id, shop_id, full_name, role, bio) VALUES
('22222222-0000-0000-0000-000000000001'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Anna Rossi', 'stilista senior', 'Stilista di fama internazionale'),
('22222222-0000-0000-0000-000000000002'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Luca Neri', 'colorista', 'Esperto di balayage e meches');

-- ============================================================
-- SERVICES — Shop A
-- ============================================================
INSERT INTO services (id, shop_id, service_name, description, duration_minutes, price_eur, category) VALUES
('aaaa0001-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Taglio donna', 'Taglio, shampoo e piega', 45, 35.00, 'taglio'),
('aaaa0001-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Taglio uomo', 'Taglio maschile classico o moderno', 30, 25.00, 'taglio'),
('aaaa0001-0000-0000-0000-000000000003'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Colore', 'Colorazione completa', 60, 55.00, 'colore'),
('aaaa0001-0000-0000-0000-000000000004'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Meches', 'Meches o colpi di sole', 90, 70.00, 'colore'),
('aaaa0001-0000-0000-0000-000000000005'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Piega', 'Piega semplice', 30, 20.00, 'piega'),
('aaaa0001-0000-0000-0000-000000000006'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Trattamento cheratina', 'Trattamento lisciante alla cheratina', 120, 90.00, 'trattamento');

-- SERVICES — Shop B
INSERT INTO services (id, shop_id, service_name, description, duration_minutes, price_eur, category) VALUES
('bbbb0001-0000-0000-0000-000000000001'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Taglio donna', 'Taglio con consulenza personalizzata', 50, 45.00, 'taglio'),
('bbbb0001-0000-0000-0000-000000000002'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Colore', 'Colorazione premium', 75, 80.00, 'colore'),
('bbbb0001-0000-0000-0000-000000000003'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Balayage', 'Balayage naturale', 120, 120.00, 'colore'),
('bbbb0001-0000-0000-0000-000000000004'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Piega', 'Piega professionale', 30, 30.00, 'piega');

-- ============================================================
-- STAFF_SERVICES — Shop A
-- ============================================================
-- Mirco: taglio donna, taglio uomo, piega
INSERT INTO staff_services (staff_id, service_id) VALUES
('11111111-0000-0000-0000-000000000001'::uuid, 'aaaa0001-0000-0000-0000-000000000001'::uuid),
('11111111-0000-0000-0000-000000000001'::uuid, 'aaaa0001-0000-0000-0000-000000000002'::uuid),
('11111111-0000-0000-0000-000000000001'::uuid, 'aaaa0001-0000-0000-0000-000000000005'::uuid);
-- Giulia: colore, meches, cheratina, piega
INSERT INTO staff_services (staff_id, service_id) VALUES
('11111111-0000-0000-0000-000000000002'::uuid, 'aaaa0001-0000-0000-0000-000000000003'::uuid),
('11111111-0000-0000-0000-000000000002'::uuid, 'aaaa0001-0000-0000-0000-000000000004'::uuid),
('11111111-0000-0000-0000-000000000002'::uuid, 'aaaa0001-0000-0000-0000-000000000005'::uuid),
('11111111-0000-0000-0000-000000000002'::uuid, 'aaaa0001-0000-0000-0000-000000000006'::uuid);
-- Marco: taglio donna, taglio uomo, piega
INSERT INTO staff_services (staff_id, service_id) VALUES
('11111111-0000-0000-0000-000000000003'::uuid, 'aaaa0001-0000-0000-0000-000000000001'::uuid),
('11111111-0000-0000-0000-000000000003'::uuid, 'aaaa0001-0000-0000-0000-000000000002'::uuid),
('11111111-0000-0000-0000-000000000003'::uuid, 'aaaa0001-0000-0000-0000-000000000005'::uuid);

-- STAFF_SERVICES — Shop B
-- Anna: taglio, colore, balayage, piega
INSERT INTO staff_services (staff_id, service_id) VALUES
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000001'::uuid),
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000002'::uuid),
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000003'::uuid),
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000004'::uuid);
-- Luca: colore, balayage
INSERT INTO staff_services (staff_id, service_id) VALUES
('22222222-0000-0000-0000-000000000002'::uuid, 'bbbb0001-0000-0000-0000-000000000002'::uuid),
('22222222-0000-0000-0000-000000000002'::uuid, 'bbbb0001-0000-0000-0000-000000000003'::uuid);

-- ============================================================
-- STAFF_SCHEDULES — All staff 10:00-18:00 Mon-Sat (MVP)
-- day_of_week: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat
-- ============================================================
INSERT INTO staff_schedules (staff_id, day_of_week, start_time, end_time)
SELECT s.id, d.day, '10:00'::time, '18:00'::time
FROM staff s
CROSS JOIN (VALUES (0),(1),(2),(3),(4),(5)) AS d(day);

-- ============================================================
-- SAMPLE CUSTOMERS — Shop A
-- ============================================================
INSERT INTO customers (id, shop_id, full_name, preferred_staff_id) VALUES
('cccc0001-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Maria Rossi', '11111111-0000-0000-0000-000000000001'::uuid),
('cccc0001-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Luca Ferrari', NULL);

INSERT INTO phone_contacts (phone_number, customer_id) VALUES
('+39 333 1111111', 'cccc0001-0000-0000-0000-000000000001'::uuid),
('+39 333 2222222', 'cccc0001-0000-0000-0000-000000000002'::uuid);

-- SAMPLE CUSTOMERS — Shop B
INSERT INTO customers (id, shop_id, full_name) VALUES
('cccc0002-0000-0000-0000-000000000001'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Francesca Bianchi');

INSERT INTO phone_contacts (phone_number, customer_id) VALUES
('+39 333 3333333', 'cccc0002-0000-0000-0000-000000000001'::uuid);

-- ============================================================
-- SAMPLE APPOINTMENTS — Shop A (next week for testing)
-- ============================================================
INSERT INTO appointments (id, shop_id, customer_id, staff_id, start_time, end_time, status) VALUES
('dddd0001-0000-0000-0000-000000000001'::uuid,
 'a0000000-0000-0000-0000-000000000001'::uuid,
 'cccc0001-0000-0000-0000-000000000001'::uuid,
 '11111111-0000-0000-0000-000000000001'::uuid,
 '2026-03-30 10:00:00+01', '2026-03-30 10:45:00+01', 'scheduled');

INSERT INTO appointment_services (appointment_id, service_id, duration_minutes, price_eur) VALUES
('dddd0001-0000-0000-0000-000000000001'::uuid, 'aaaa0001-0000-0000-0000-000000000001'::uuid, 45, 35.00);
```

- [ ] **Step 3: Write available_slots() function**

Create `lakebase/sql/03_functions.sql`:

```sql
-- available_slots: find open appointment slots for a shop
-- Accepts an array of service_ids, sums their durations,
-- and returns only staff capable of performing ALL requested services.
SET search_path TO hair_salon;

CREATE OR REPLACE FUNCTION available_slots(
    p_shop_id UUID,
    p_from TIMESTAMPTZ,
    p_to TIMESTAMPTZ,
    p_service_ids UUID[],
    p_staff_id UUID DEFAULT NULL
)
RETURNS TABLE (
    staff_id UUID,
    staff_name TEXT,
    slot_start TIMESTAMPTZ,
    slot_end TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_minutes INTEGER;
    v_num_services INTEGER;
BEGIN
    -- Compute total duration from requested services
    v_num_services := array_length(p_service_ids, 1);

    SELECT COALESCE(SUM(s.duration_minutes), 0)
    INTO v_total_minutes
    FROM services s
    WHERE s.id = ANY(p_service_ids) AND s.is_active;

    IF v_total_minutes = 0 THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH eligible_staff AS (
        -- Staff who can perform ALL requested services
        SELECT st.id AS staff_id, st.full_name AS staff_name
        FROM staff st
        WHERE st.shop_id = p_shop_id
          AND st.is_active
          AND (p_staff_id IS NULL OR st.id = p_staff_id)
          AND (
              SELECT COUNT(DISTINCT ss.service_id)
              FROM staff_services ss
              WHERE ss.staff_id = st.id
                AND ss.service_id = ANY(p_service_ids)
          ) = v_num_services
    ),
    date_range AS (
        -- Generate each day in the range
        SELECT d::date AS day
        FROM generate_series(p_from::date, p_to::date, '1 day'::interval) d
    ),
    schedule_windows AS (
        -- For each eligible staff + day, get their work window
        SELECT
            es.staff_id,
            es.staff_name,
            (dr.day + sch.start_time) AT TIME ZONE 'Europe/Rome' AS window_start,
            (dr.day + sch.end_time) AT TIME ZONE 'Europe/Rome' AS window_end
        FROM eligible_staff es
        JOIN date_range dr ON true
        JOIN staff_schedules sch
            ON sch.staff_id = es.staff_id
            AND sch.day_of_week = EXTRACT(ISODOW FROM dr.day)::INT - 1
    ),
    candidate_slots AS (
        -- Generate 30-min-granularity slot starts within each window
        SELECT
            sw.staff_id,
            sw.staff_name,
            gs AS slot_start,
            gs + (v_total_minutes || ' minutes')::interval AS slot_end
        FROM schedule_windows sw
        CROSS JOIN LATERAL generate_series(
            sw.window_start,
            sw.window_end - (v_total_minutes || ' minutes')::interval,
            '30 minutes'::interval
        ) gs
        WHERE gs >= p_from
          AND gs + (v_total_minutes || ' minutes')::interval <= p_to
    )
    SELECT
        cs.staff_id,
        cs.staff_name,
        cs.slot_start,
        cs.slot_end
    FROM candidate_slots cs
    WHERE NOT EXISTS (
        -- Exclude slots that overlap with existing appointments
        SELECT 1
        FROM appointments a
        WHERE a.staff_id = cs.staff_id
          AND a.status NOT IN ('cancelled', 'no_show')
          AND tstzrange(a.start_time, a.end_time) && tstzrange(cs.slot_start, cs.slot_end)
    )
    ORDER BY cs.slot_start, cs.staff_name;
END;
$$;
```

- [ ] **Step 4: Delete old SQL files**

```bash
rm -f lakebase/sql/01_lakebase_schema.sql lakebase/sql/02_seed_uc_data.sql
```

- [ ] **Step 5: Commit**

```bash
git add lakebase/sql/
git commit -m "feat: new hair_salon schema with multi-shop support, seed data, and available_slots function"
```

---

## Task 3: Booking Engine — Config & Database Connection

**Files:**
- Create: `booking_engine/__init__.py`
- Create: `booking_engine/config.py`
- Create: `booking_engine/db/__init__.py`
- Create: `booking_engine/db/connection.py`
- Test: `tests/booking_engine/test_connection.py`

- [ ] **Step 1: Write the test for config loading**

Create `tests/booking_engine/test_config.py`:

```python
import os
from unittest.mock import patch

def test_settings_from_env():
    env = {
        "LAKEBASE_HOST": "test-host",
        "LAKEBASE_PORT": "5432",
        "LAKEBASE_DB": "testdb",
        "LAKEBASE_USER": "testuser",
        "LAKEBASE_PASSWORD": "testpass",
        "LAKEBASE_SCHEMA": "hair_salon",
    }
    with patch.dict(os.environ, env, clear=False):
        from booking_engine.config import Settings
        s = Settings()
        assert s.lakebase_host == "test-host"
        assert s.lakebase_port == 5432
        assert s.lakebase_schema == "hair_salon"
```

- [ ] **Step 2: Run test — expect fail**

```bash
pytest tests/booking_engine/test_config.py -v
# Expected: ModuleNotFoundError: No module named 'booking_engine'
```

- [ ] **Step 3: Implement config**

Create `booking_engine/__init__.py` (empty).

Create `booking_engine/config.py`:

```python
"""Booking Engine configuration from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    lakebase_host: str
    lakebase_port: int = 5432
    lakebase_db: str = "databricks_postgres"
    lakebase_user: str = "authenticator"
    lakebase_password: str = ""
    lakebase_schema: str = "hair_salon"
    lakebase_sslmode: str = "require"

    @property
    def dsn(self) -> str:
        return (
            f"host={self.lakebase_host} port={self.lakebase_port} "
            f"dbname={self.lakebase_db} user={self.lakebase_user} "
            f"password={self.lakebase_password} sslmode={self.lakebase_sslmode}"
        )

    model_config = {"env_prefix": ""}
```

- [ ] **Step 4: Run test — expect pass**

```bash
pytest tests/booking_engine/test_config.py -v
# Expected: PASSED
```

- [ ] **Step 5: Write DB connection module**

Create `booking_engine/db/__init__.py` (empty).

Create `booking_engine/db/connection.py`:

```python
"""Async connection pool for Lakebase (PostgreSQL via psycopg v3)."""
from __future__ import annotations

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from booking_engine.config import Settings

_pool: AsyncConnectionPool | None = None


async def init_pool(settings: Settings) -> AsyncConnectionPool:
    """Create and open the connection pool. Called once at app startup."""
    global _pool
    schema = settings.lakebase_schema

    async def configure_conn(conn):
        """Set search_path on every connection checkout."""
        await conn.execute(
            "SET search_path TO %s", (schema,)
        )

    _pool = AsyncConnectionPool(
        conninfo=settings.dsn,
        min_size=2,
        max_size=10,
        kwargs={"row_factory": dict_row},
        configure=configure_conn,
        open=False,
    )
    await _pool.open()
    return _pool


async def get_pool() -> AsyncConnectionPool:
    """Return the active pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def close_pool() -> None:
    """Close the pool. Called at app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
```

- [ ] **Step 6: Commit**

```bash
git add booking_engine/ tests/booking_engine/
git commit -m "feat(booking-engine): add config and async database connection pool"
```

---

## Task 4: Booking Engine — Pydantic Models & Error Schema

**Files:**
- Create: `booking_engine/api/__init__.py`
- Create: `booking_engine/api/models.py`
- Test: `tests/booking_engine/test_models.py`

- [ ] **Step 1: Write model tests**

Create `tests/booking_engine/test_models.py`:

```python
import pytest
from uuid import uuid4
from datetime import datetime, date
from decimal import Decimal


def test_shop_response_serialization():
    from booking_engine.api.models import ShopResponse
    shop = ShopResponse(
        id=uuid4(), name="Salon Bella", phone_number="+39 02 123",
        address="Via Roma", welcome_message="Ciao!", tone_instructions="friendly",
        personality="sunny", special_instructions=None, is_active=True,
    )
    data = shop.model_dump()
    assert data["name"] == "Salon Bella"
    assert data["special_instructions"] is None


def test_available_slot_response():
    from booking_engine.api.models import AvailableSlotResponse
    slot = AvailableSlotResponse(
        staff_id=uuid4(), staff_name="Mirco",
        slot_start=datetime(2026, 3, 30, 10, 0),
        slot_end=datetime(2026, 3, 30, 11, 30),
    )
    assert slot.staff_name == "Mirco"


def test_create_appointment_request_validation():
    from booking_engine.api.models import CreateAppointmentRequest
    req = CreateAppointmentRequest(
        customer_id=uuid4(), service_ids=[uuid4()],
        staff_id=uuid4(), start_time=datetime(2026, 3, 30, 10, 0),
    )
    assert len(req.service_ids) == 1


def test_error_response():
    from booking_engine.api.models import ErrorResponse
    err = ErrorResponse(error="slot_taken", message="Slot already booked")
    assert err.error == "slot_taken"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/booking_engine/test_models.py -v
# Expected: ModuleNotFoundError
```

- [ ] **Step 3: Implement models**

Create `booking_engine/api/__init__.py` (empty).

Create `booking_engine/api/models.py`:

```python
"""Pydantic models for Booking Engine API requests and responses."""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Error ──────────────────────────────────────────────────
class ErrorResponse(BaseModel):
    error: str
    message: str


# ── Shops ──────────────────────────────────────────────────
class ShopResponse(BaseModel):
    id: UUID
    name: str
    phone_number: str | None = None
    address: str | None = None
    welcome_message: str | None = None
    tone_instructions: str | None = None
    personality: str | None = None
    special_instructions: str | None = None
    is_active: bool


# ── Staff ──────────────────────────────────────────────────
class StaffResponse(BaseModel):
    id: UUID
    full_name: str
    role: str | None = None
    bio: str | None = None


# ── Services ───────────────────────────────────────────────
class ServiceResponse(BaseModel):
    id: UUID
    service_name: str
    description: str | None = None
    duration_minutes: int
    price_eur: Decimal | None = None
    category: str | None = None


# ── Customers ──────────────────────────────────────────────
class CustomerResponse(BaseModel):
    id: UUID
    full_name: str
    preferred_staff_id: UUID | None = None
    notes: str | None = None


class CreateCustomerRequest(BaseModel):
    full_name: str
    phone_number: str | None = None


# ── Availability ───────────────────────────────────────────
class AvailableSlotResponse(BaseModel):
    staff_id: UUID
    staff_name: str
    slot_start: datetime
    slot_end: datetime


class AvailabilityResponse(BaseModel):
    slots: list[AvailableSlotResponse]
    suggestions: list[AvailableSlotResponse] | None = None


# ── Appointments ───────────────────────────────────────────
class AppointmentServiceDetail(BaseModel):
    service_id: UUID
    service_name: str | None = None
    duration_minutes: int
    price_eur: Decimal | None = None


class AppointmentResponse(BaseModel):
    id: UUID
    customer_id: UUID
    staff_id: UUID
    staff_name: str | None = None
    start_time: datetime
    end_time: datetime
    status: str
    services: list[AppointmentServiceDetail] = []
    notes: str | None = None


class CreateAppointmentRequest(BaseModel):
    customer_id: UUID
    service_ids: list[UUID] = Field(min_length=1)
    staff_id: UUID
    start_time: datetime
    notes: str | None = None


class RescheduleRequest(BaseModel):
    new_start_time: datetime
    new_staff_id: UUID | None = None
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/booking_engine/test_models.py -v
# Expected: all PASSED
```

- [ ] **Step 5: Commit**

```bash
git add booking_engine/api/ tests/booking_engine/test_models.py
git commit -m "feat(booking-engine): add Pydantic models for all API endpoints"
```

---

## Task 5: Booking Engine — Database Query Layer

**Files:**
- Create: `booking_engine/db/queries.py`
- Test: `tests/booking_engine/test_queries.py`

This task defines all SQL queries as async functions. Tests use mocked connections.

- [ ] **Step 1: Write query tests**

Create `tests/booking_engine/test_queries.py`:

```python
"""Tests for query functions using mocked DB connections."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID


SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")
STAFF_1 = UUID("11111111-0000-0000-0000-000000000001")
SERVICE_1 = UUID("aaaa0001-0000-0000-0000-000000000001")


@pytest.fixture
def mock_pool():
    """Create a mock async connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    cursor = AsyncMock()

    # Make pool.connection() work as async context manager
    pool.connection.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.connection.return_value.__aexit__ = AsyncMock(return_value=False)

    conn.execute.return_value = cursor
    cursor.fetchall = AsyncMock(return_value=[])
    cursor.fetchone = AsyncMock(return_value=None)

    return pool, conn, cursor


@pytest.mark.asyncio
async def test_get_shop_returns_dict(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchone = AsyncMock(return_value={"id": SHOP_A, "name": "Salon Bella", "is_active": True})

    from booking_engine.db.queries import get_shop
    result = await get_shop(pool, SHOP_A)
    assert result["name"] == "Salon Bella"


@pytest.mark.asyncio
async def test_get_shop_not_found(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchone = AsyncMock(return_value=None)

    from booking_engine.db.queries import get_shop
    result = await get_shop(pool, SHOP_A)
    assert result is None


@pytest.mark.asyncio
async def test_list_services(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchall = AsyncMock(return_value=[
        {"id": SERVICE_1, "service_name": "Taglio", "duration_minutes": 30},
    ])

    from booking_engine.db.queries import list_services
    result = await list_services(pool, SHOP_A)
    assert len(result) == 1
    assert result[0]["service_name"] == "Taglio"


@pytest.mark.asyncio
async def test_find_customers_by_phone(mock_pool):
    pool, conn, cursor = mock_pool
    cursor.fetchall = AsyncMock(return_value=[
        {"id": UUID("cccc0001-0000-0000-0000-000000000001"), "full_name": "Maria Rossi"},
    ])

    from booking_engine.db.queries import find_customers_by_phone
    result = await find_customers_by_phone(pool, SHOP_A, "+39 333 1111111")
    assert len(result) == 1
    assert result[0]["full_name"] == "Maria Rossi"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/booking_engine/test_queries.py -v
# Expected: ModuleNotFoundError
```

- [ ] **Step 3: Implement queries**

Create `booking_engine/db/queries.py`:

```python
"""SQL query functions for all Booking Engine operations."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from psycopg_pool import AsyncConnectionPool
from psycopg.sql import SQL, Identifier

_ROME = ZoneInfo("Europe/Rome")


# ── Shops ──────────────────────────────────────────────────

async def get_shop(pool: AsyncConnectionPool, shop_id: UUID) -> dict | None:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT * FROM shops WHERE id = %s AND is_active", (shop_id,)
        )
        return await cur.fetchone()


# ── Staff ──────────────────────────────────────────────────

async def list_staff(pool: AsyncConnectionPool, shop_id: UUID) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, full_name, role, bio FROM staff "
            "WHERE shop_id = %s AND is_active ORDER BY full_name",
            (shop_id,),
        )
        return await cur.fetchall()


async def get_staff_services(
    pool: AsyncConnectionPool, staff_id: UUID
) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT s.id, s.service_name, s.duration_minutes, s.price_eur, s.category "
            "FROM services s JOIN staff_services ss ON s.id = ss.service_id "
            "WHERE ss.staff_id = %s AND s.is_active ORDER BY s.service_name",
            (staff_id,),
        )
        return await cur.fetchall()


# ── Services ───────────────────────────────────────────────

async def list_services(pool: AsyncConnectionPool, shop_id: UUID) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT id, service_name, description, duration_minutes, price_eur, category "
            "FROM services WHERE shop_id = %s AND is_active ORDER BY category, service_name",
            (shop_id,),
        )
        return await cur.fetchall()


# ── Customers ──────────────────────────────────────────────

async def find_customers_by_phone(
    pool: AsyncConnectionPool, shop_id: UUID, phone: str
) -> list[dict]:
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


async def upsert_phone_contact(
    pool: AsyncConnectionPool, phone: str, customer_id: UUID
) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO phone_contacts (phone_number, customer_id) "
            "VALUES (%s, %s) ON CONFLICT (phone_number, customer_id) "
            "DO UPDATE SET last_seen_at = now()",
            (phone, customer_id),
        )


# ── Availability ───────────────────────────────────────────

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


# ── Appointments ───────────────────────────────────────────

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
            # Sum service durations
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

            # Insert appointment
            cur = await conn.execute(
                "INSERT INTO appointments "
                "(shop_id, customer_id, staff_id, start_time, end_time, status, notes) "
                "VALUES (%s, %s, %s, %s, %s, 'scheduled', %s) RETURNING *",
                (shop_id, customer_id, staff_id, start_time, end_time, notes),
            )
            appointment = await cur.fetchone()

            # Insert appointment_services
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

        # Attach services
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
            # Get current appointment
            cur = await conn.execute(
                "SELECT * FROM appointments "
                "WHERE id = %s AND shop_id = %s AND status IN ('scheduled', 'confirmed')",
                (appointment_id, shop_id),
            )
            current = await cur.fetchone()
            if not current:
                return None

            # Compute new end_time from same duration
            duration = current["end_time"] - current["start_time"]
            new_end = new_start_time + duration
            staff = new_staff_id or current["staff_id"]

            # Cancel old
            await conn.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = %s",
                (appointment_id,),
            )

            # Create new
            cur = await conn.execute(
                "INSERT INTO appointments "
                "(shop_id, customer_id, staff_id, start_time, end_time, status, notes) "
                "VALUES (%s, %s, %s, %s, %s, 'scheduled', %s) RETURNING *",
                (shop_id, current["customer_id"], staff, new_start_time, new_end, current["notes"]),
            )
            new_appt = await cur.fetchone()

            # Copy services from old appointment
            await conn.execute(
                "INSERT INTO appointment_services (appointment_id, service_id, duration_minutes, price_eur) "
                "SELECT %s, service_id, duration_minutes, price_eur "
                "FROM appointment_services WHERE appointment_id = %s",
                (new_appt["id"], appointment_id),
            )

            return new_appt
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/booking_engine/test_queries.py -v
# Expected: all PASSED
```

- [ ] **Step 5: Commit**

```bash
git add booking_engine/db/queries.py tests/booking_engine/test_queries.py
git commit -m "feat(booking-engine): add async SQL query functions for all entities"
```

---

## Task 6: Booking Engine — API Routes (Shops, Services, Staff, Customers)

**Files:**
- Create: `booking_engine/api/routes/__init__.py`
- Create: `booking_engine/api/routes/shops.py`
- Create: `booking_engine/api/routes/customers.py`
- Create: `booking_engine/api/routes/services.py`
- Test: `tests/booking_engine/test_routes_shops.py`
- Test: `tests/booking_engine/test_routes_customers.py`
- Test: `tests/booking_engine/test_routes_services.py`

- [ ] **Step 1: Write route tests for shops**

Create `tests/booking_engine/test_routes_shops.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from uuid import UUID

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")

MOCK_SHOP = {
    "id": SHOP_A, "name": "Salon Bella", "phone_number": "+39 02 123",
    "address": "Via Roma", "welcome_message": "Ciao!", "tone_instructions": "friendly",
    "personality": "sunny", "special_instructions": None, "is_active": True,
}


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def app(mock_pool):
    from booking_engine.api.app import create_app
    application = create_app()
    application.state.pool = mock_pool
    return application


@pytest.mark.asyncio
async def test_get_shop_success(app, mock_pool):
    with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock) as mock:
        mock.return_value = MOCK_SHOP
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/shops/{SHOP_A}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Salon Bella"


@pytest.mark.asyncio
async def test_get_shop_not_found(app, mock_pool):
    with patch("booking_engine.api.routes.shops.get_shop", new_callable=AsyncMock) as mock:
        mock.return_value = None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/shops/{SHOP_A}")
        assert resp.status_code == 404
        assert resp.json()["error"] == "shop_not_found"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/booking_engine/test_routes_shops.py -v
```

- [ ] **Step 3: Create the FastAPI app factory**

Create `booking_engine/api/app.py`:

```python
"""Booking Engine FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool

from booking_engine.config import Settings
from booking_engine.db.connection import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    pool = await init_pool(settings)
    app.state.pool = pool
    yield
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="Hair Salon Booking Engine", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    from booking_engine.api.routes import shops, customers, services, availability, appointments
    app.include_router(shops.router, prefix="/api/v1")
    app.include_router(customers.router, prefix="/api/v1")
    app.include_router(services.router, prefix="/api/v1")
    app.include_router(availability.router, prefix="/api/v1")
    app.include_router(appointments.router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def get_pool(request: Request) -> AsyncConnectionPool:
    return request.app.state.pool
```

- [ ] **Step 4: Implement shops route**

Create `booking_engine/api/routes/__init__.py` (empty).

Create `booking_engine/api/routes/shops.py`:

```python
"""Shop configuration routes."""
from uuid import UUID

from fastapi import APIRouter, Depends
from psycopg_pool import AsyncConnectionPool

from booking_engine.api.app import get_pool
from booking_engine.api.models import ShopResponse, ErrorResponse
from booking_engine.db.queries import get_shop

router = APIRouter(tags=["shops"])


@router.get(
    "/shops/{shop_id}",
    response_model=ShopResponse,
    responses={404: {"model": ErrorResponse}},
)
async def read_shop(shop_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)):
    shop = await get_shop(pool, shop_id)
    if not shop:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"error": "shop_not_found", "message": f"Shop {shop_id} not found"},
        )
    return shop
```

- [ ] **Step 5: Implement services route**

Create `booking_engine/api/routes/services.py`:

```python
"""Services and staff routes."""
from uuid import UUID

from fastapi import APIRouter, Depends
from psycopg_pool import AsyncConnectionPool

from booking_engine.api.app import get_pool
from booking_engine.api.models import ServiceResponse, StaffResponse, ErrorResponse
from booking_engine.db.queries import list_services, list_staff, get_staff_services

router = APIRouter(tags=["services"])


@router.get("/shops/{shop_id}/services", response_model=list[ServiceResponse])
async def read_services(shop_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)):
    return await list_services(pool, shop_id)


@router.get("/shops/{shop_id}/staff", response_model=list[StaffResponse])
async def read_staff(shop_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)):
    return await list_staff(pool, shop_id)


@router.get(
    "/shops/{shop_id}/staff/{staff_id}/services",
    response_model=list[ServiceResponse],
)
async def read_staff_services(
    shop_id: UUID, staff_id: UUID, pool: AsyncConnectionPool = Depends(get_pool)
):
    return await get_staff_services(pool, staff_id)
```

- [ ] **Step 6: Implement customers route**

Create `booking_engine/api/routes/customers.py`:

```python
"""Customer lookup and creation routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from psycopg_pool import AsyncConnectionPool

from booking_engine.api.app import get_pool
from booking_engine.api.models import CustomerResponse, CreateCustomerRequest, ErrorResponse
from booking_engine.db.queries import (
    find_customers_by_phone, find_customers_by_name_and_phone,
    create_customer, upsert_phone_contact,
)

router = APIRouter(tags=["customers"])


@router.get("/shops/{shop_id}/customers", response_model=list[CustomerResponse])
async def lookup_customers(
    shop_id: UUID,
    phone: str | None = Query(None),
    name: str | None = Query(None),
    pool: AsyncConnectionPool = Depends(get_pool),
):
    if phone and name:
        return await find_customers_by_name_and_phone(pool, shop_id, name, phone)
    elif phone:
        return await find_customers_by_phone(pool, shop_id, phone)
    return []


@router.post(
    "/shops/{shop_id}/customers",
    response_model=CustomerResponse,
    status_code=201,
)
async def create_new_customer(
    shop_id: UUID,
    body: CreateCustomerRequest,
    pool: AsyncConnectionPool = Depends(get_pool),
):
    return await create_customer(pool, shop_id, body.full_name, body.phone_number)
```

- [ ] **Step 7: Run tests — expect pass**

```bash
pytest tests/booking_engine/test_routes_shops.py -v
# Expected: all PASSED
```

- [ ] **Step 8: Commit**

```bash
git add booking_engine/api/ tests/booking_engine/test_routes_*.py
git commit -m "feat(booking-engine): add API routes for shops, services, staff, and customers"
```

---

## Task 7: Booking Engine — Availability & Appointment Routes

**Files:**
- Create: `booking_engine/api/routes/availability.py`
- Create: `booking_engine/api/routes/appointments.py`
- Test: `tests/booking_engine/test_routes_availability.py`
- Test: `tests/booking_engine/test_routes_appointments.py`

- [ ] **Step 1: Write availability route tests**

Create `tests/booking_engine/test_routes_availability.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from uuid import UUID
from datetime import datetime

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")
STAFF_1 = UUID("11111111-0000-0000-0000-000000000001")
SERVICE_1 = UUID("aaaa0001-0000-0000-0000-000000000001")


@pytest.fixture
def app():
    from booking_engine.api.app import create_app
    application = create_app()
    application.state.pool = AsyncMock()
    return application


@pytest.mark.asyncio
async def test_availability_returns_slots(app):
    mock_slots = [
        {"staff_id": STAFF_1, "staff_name": "Mirco", "slot_start": datetime(2026,3,30,10,0), "slot_end": datetime(2026,3,30,10,45)},
    ]
    with patch("booking_engine.api.routes.availability.get_available_slots", new_callable=AsyncMock) as mock:
        mock.return_value = mock_slots
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/shops/{SHOP_A}/availability",
                params={"service_ids": str(SERVICE_1), "start_date": "2026-03-30", "end_date": "2026-03-30"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["slots"]) == 1
    assert data["slots"][0]["staff_name"] == "Mirco"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/booking_engine/test_routes_availability.py -v
```

- [ ] **Step 3: Implement availability route**

Create `booking_engine/api/routes/availability.py`:

```python
"""Availability check route with suggestion fallback."""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from psycopg_pool import AsyncConnectionPool

from booking_engine.api.app import get_pool
from booking_engine.api.models import AvailabilityResponse
from booking_engine.db.queries import get_available_slots

router = APIRouter(tags=["availability"])


@router.get("/shops/{shop_id}/availability", response_model=AvailabilityResponse)
async def check_availability(
    shop_id: UUID,
    service_ids: str = Query(..., description="Comma-separated service UUIDs"),
    start_date: date = Query(...),
    end_date: date = Query(...),
    staff_id: UUID | None = Query(None),
    pool: AsyncConnectionPool = Depends(get_pool),
):
    parsed_ids = [UUID(sid.strip()) for sid in service_ids.split(",")]

    slots = await get_available_slots(pool, shop_id, parsed_ids, start_date, end_date, staff_id)

    suggestions = None
    if not slots and staff_id:
        # Preferred staff unavailable — find alternatives within 3 working days
        fallback_end = _add_working_days(start_date, 3)
        suggestions = await get_available_slots(
            pool, shop_id, parsed_ids, start_date, fallback_end, staff_id=None,
        )

    return AvailabilityResponse(slots=slots, suggestions=suggestions)


def _add_working_days(start: date, days: int) -> date:
    """Add N working days (Mon-Sat) to a date."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 6:  # Mon=0 .. Sat=5
            added += 1
    return current
```

- [ ] **Step 4: Implement appointments route**

Create `booking_engine/api/routes/appointments.py`:

```python
"""Appointment CRUD routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from psycopg_pool import AsyncConnectionPool
from psycopg.errors import ExclusionViolation

from booking_engine.api.app import get_pool
from booking_engine.api.models import (
    AppointmentResponse, CreateAppointmentRequest, RescheduleRequest, ErrorResponse,
)
from booking_engine.db.queries import (
    create_appointment, list_appointments, cancel_appointment, reschedule_appointment,
)

router = APIRouter(tags=["appointments"])


@router.post(
    "/shops/{shop_id}/appointments",
    response_model=AppointmentResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
)
async def book_appointment(
    shop_id: UUID,
    body: CreateAppointmentRequest,
    pool: AsyncConnectionPool = Depends(get_pool),
):
    try:
        appt = await create_appointment(
            pool, shop_id, body.customer_id, body.staff_id,
            body.service_ids, body.start_time, body.notes,
        )
        return appt
    except ExclusionViolation:
        return JSONResponse(
            status_code=409,
            content={"error": "slot_taken", "message": "Time slot is already booked"},
        )


@router.get("/shops/{shop_id}/appointments", response_model=list[AppointmentResponse])
async def read_appointments(
    shop_id: UUID,
    customer_id: UUID | None = Query(None),
    status: str | None = Query(None),
    pool: AsyncConnectionPool = Depends(get_pool),
):
    return await list_appointments(pool, shop_id, customer_id, status)


@router.patch(
    "/shops/{shop_id}/appointments/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def cancel(
    shop_id: UUID,
    appointment_id: UUID,
    pool: AsyncConnectionPool = Depends(get_pool),
):
    result = await cancel_appointment(pool, shop_id, appointment_id)
    if not result:
        return JSONResponse(
            status_code=409,
            content={"error": "appointment_not_cancellable", "message": "Appointment cannot be cancelled"},
        )
    return result


@router.patch(
    "/shops/{shop_id}/appointments/{appointment_id}/reschedule",
    response_model=AppointmentResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def reschedule(
    shop_id: UUID,
    appointment_id: UUID,
    body: RescheduleRequest,
    pool: AsyncConnectionPool = Depends(get_pool),
):
    try:
        result = await reschedule_appointment(
            pool, shop_id, appointment_id, body.new_start_time, body.new_staff_id,
        )
        if not result:
            return JSONResponse(
                status_code=404,
                content={"error": "appointment_not_found", "message": "Appointment not found or not reschedulable"},
            )
        return result
    except ExclusionViolation:
        return JSONResponse(
            status_code=409,
            content={"error": "slot_taken", "message": "New time slot is already booked"},
        )
```

- [ ] **Step 5: Run tests — expect pass**

```bash
pytest tests/booking_engine/test_routes_availability.py -v
# Expected: PASSED
```

- [ ] **Step 6: Commit**

```bash
git add booking_engine/api/routes/ tests/booking_engine/test_routes_availability.py tests/booking_engine/test_routes_appointments.py
git commit -m "feat(booking-engine): add availability and appointment routes with suggestion fallback"
```

---

## Task 8: Booking Engine — Databricks App Config

**Files:**
- Create: `booking_engine/app.yaml`

- [ ] **Step 1: Create app.yaml**

Create `booking_engine/app.yaml`:

```yaml
command:
  - uvicorn
  - booking_engine.api.app:create_app
  - --host=0.0.0.0
  - --port=8000
  - --factory

env:
  - name: LAKEBASE_HOST
    description: Lakebase PostgreSQL host
  - name: LAKEBASE_PORT
    value: "5432"
  - name: LAKEBASE_DB
    value: "databricks_postgres"
  - name: LAKEBASE_USER
    description: Lakebase username
  - name: LAKEBASE_PASSWORD
    description: Lakebase password
  - name: LAKEBASE_SCHEMA
    value: "hair_salon"
```

- [ ] **Step 2: Commit**

```bash
git add booking_engine/app.yaml
git commit -m "feat(booking-engine): add Databricks App configuration"
```

---

## Task 9: Voice Gateway — Config & Booking Client

**Files:**
- Create: `voice_gateway/__init__.py`
- Create: `voice_gateway/config.py`
- Create: `voice_gateway/clients/__init__.py`
- Create: `voice_gateway/clients/booking_client.py`
- Test: `tests/voice_gateway/test_booking_client.py`

- [ ] **Step 1: Write booking client tests**

Create `tests/voice_gateway/test_booking_client.py`:

```python
import pytest
from uuid import UUID
from datetime import date

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_get_shop_config(httpx_mock):
    httpx_mock.add_response(
        url=f"http://booking:8000/api/v1/shops/{SHOP_A}",
        json={"id": str(SHOP_A), "name": "Salon Bella", "is_active": True,
              "phone_number": None, "address": None, "welcome_message": "Ciao!",
              "tone_instructions": "friendly", "personality": "sunny",
              "special_instructions": None},
    )
    from voice_gateway.clients.booking_client import BookingClient
    client = BookingClient(base_url="http://booking:8000")
    async with client:
        shop = await client.get_shop(SHOP_A)
    assert shop["name"] == "Salon Bella"


@pytest.mark.asyncio
async def test_get_shop_not_found(httpx_mock):
    httpx_mock.add_response(
        url=f"http://booking:8000/api/v1/shops/{SHOP_A}",
        status_code=404,
        json={"error": "shop_not_found", "message": "Not found"},
    )
    from voice_gateway.clients.booking_client import BookingClient
    client = BookingClient(base_url="http://booking:8000")
    async with client:
        shop = await client.get_shop(SHOP_A)
    assert shop is None
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/voice_gateway/test_booking_client.py -v
```

- [ ] **Step 3: Implement config and booking client**

Create `voice_gateway/__init__.py` (empty).

Create `voice_gateway/config.py`:

```python
"""Voice Gateway configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    booking_engine_url: str = "http://localhost:8000"
    databricks_host: str = ""
    databricks_token: str = ""
    stt_endpoint: str = "whisper-stt-endpoint"
    tts_endpoint: str = "kokoro-tts-endpoint"
    intent_llm_endpoint: str = "databricks-meta-llama-3-1-8b-instruct"
    response_llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct"

    model_config = {"env_prefix": ""}
```

Create `voice_gateway/clients/__init__.py` (empty).

Create `voice_gateway/clients/booking_client.py`:

```python
"""Async HTTP client for the Booking Engine API."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import httpx


class BookingClient:
    """Thin async wrapper around the Booking Engine REST API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self._base = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=self._base, timeout=30.0)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("BookingClient not entered as context manager")
        return self._client

    # ── Shops ──────────────────────────────────────────

    async def get_shop(self, shop_id: UUID) -> dict | None:
        r = await self.client.get(f"/api/v1/shops/{shop_id}")
        return r.json() if r.status_code == 200 else None

    # ── Customers ──────────────────────────────────────

    async def find_customers_by_phone(self, shop_id: UUID, phone: str) -> list[dict]:
        r = await self.client.get(f"/api/v1/shops/{shop_id}/customers", params={"phone": phone})
        return r.json() if r.status_code == 200 else []

    async def find_customer_by_name_phone(
        self, shop_id: UUID, name: str, phone: str
    ) -> list[dict]:
        r = await self.client.get(
            f"/api/v1/shops/{shop_id}/customers", params={"name": name, "phone": phone}
        )
        return r.json() if r.status_code == 200 else []

    async def create_customer(
        self, shop_id: UUID, full_name: str, phone_number: str | None = None
    ) -> dict:
        r = await self.client.post(
            f"/api/v1/shops/{shop_id}/customers",
            json={"full_name": full_name, "phone_number": phone_number},
        )
        return r.json()

    # ── Services & Staff ───────────────────────────────

    async def get_services(self, shop_id: UUID) -> list[dict]:
        r = await self.client.get(f"/api/v1/shops/{shop_id}/services")
        return r.json()

    async def get_staff(self, shop_id: UUID) -> list[dict]:
        r = await self.client.get(f"/api/v1/shops/{shop_id}/staff")
        return r.json()

    # ── Availability ───────────────────────────────────

    async def check_availability(
        self, shop_id: UUID, service_ids: list[UUID],
        start_date: date, end_date: date, staff_id: UUID | None = None,
    ) -> dict:
        params = {
            "service_ids": ",".join(str(s) for s in service_ids),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        if staff_id:
            params["staff_id"] = str(staff_id)
        r = await self.client.get(f"/api/v1/shops/{shop_id}/availability", params=params)
        return r.json()

    # ── Appointments ───────────────────────────────────

    async def book_appointment(
        self, shop_id: UUID, customer_id: UUID, service_ids: list[UUID],
        staff_id: UUID, start_time: datetime, notes: str | None = None,
    ) -> dict:
        r = await self.client.post(
            f"/api/v1/shops/{shop_id}/appointments",
            json={
                "customer_id": str(customer_id),
                "service_ids": [str(s) for s in service_ids],
                "staff_id": str(staff_id),
                "start_time": start_time.isoformat(),
                "notes": notes,
            },
        )
        return r.json()

    async def list_appointments(
        self, shop_id: UUID, customer_id: UUID, status: str | None = None,
    ) -> list[dict]:
        params = {"customer_id": str(customer_id)}
        if status:
            params["status"] = status
        r = await self.client.get(f"/api/v1/shops/{shop_id}/appointments", params=params)
        return r.json()

    async def cancel_appointment(self, shop_id: UUID, appointment_id: UUID) -> dict:
        r = await self.client.patch(f"/api/v1/shops/{shop_id}/appointments/{appointment_id}/cancel")
        return r.json()

    async def reschedule_appointment(
        self, shop_id: UUID, appointment_id: UUID,
        new_start_time: datetime, new_staff_id: UUID | None = None,
    ) -> dict:
        body = {"new_start_time": new_start_time.isoformat()}
        if new_staff_id:
            body["new_staff_id"] = str(new_staff_id)
        r = await self.client.patch(
            f"/api/v1/shops/{shop_id}/appointments/{appointment_id}/reschedule",
            json=body,
        )
        return r.json()
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/voice_gateway/test_booking_client.py -v
# Expected: all PASSED
```

- [ ] **Step 5: Commit**

```bash
git add voice_gateway/ tests/voice_gateway/
git commit -m "feat(voice-gateway): add config and async booking engine HTTP client"
```

---

## Task 10: Voice Gateway — Session Management & Prompt Assembler

**Files:**
- Create: `voice_gateway/conversation/__init__.py`
- Create: `voice_gateway/conversation/session.py`
- Create: `voice_gateway/conversation/prompt_assembler.py`
- Test: `tests/voice_gateway/test_session.py`
- Test: `tests/voice_gateway/test_prompt_assembler.py`

- [ ] **Step 1: Write session tests**

Create `tests/voice_gateway/test_session.py`:

```python
from uuid import uuid4
from voice_gateway.conversation.session import Session, SessionManager


def test_session_creation():
    s = Session(shop_id=uuid4(), shop_config={"name": "Salon Bella"})
    assert s.session_id is not None
    assert s.customer is None
    assert len(s.history) == 0


def test_session_add_turns():
    s = Session(shop_id=uuid4(), shop_config={"name": "Test"})
    s.add_user_turn("Ciao")
    s.add_assistant_turn("Benvenuto!")
    assert len(s.history) == 2
    assert s.history[0]["role"] == "user"
    assert s.history[1]["role"] == "assistant"


def test_session_history_sliding_window():
    s = Session(shop_id=uuid4(), shop_config={"name": "Test"}, max_history=4)
    for i in range(10):
        s.add_user_turn(f"msg {i}")
        s.add_assistant_turn(f"reply {i}")
    assert len(s.history) == 4  # sliding window


def test_session_manager_lifecycle():
    mgr = SessionManager()
    sid = mgr.create_session(shop_id=uuid4(), shop_config={"name": "Test"})
    session = mgr.get_session(sid)
    assert session is not None
    mgr.end_session(sid)
    assert mgr.get_session(sid) is None
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/voice_gateway/test_session.py -v
```

- [ ] **Step 3: Implement session**

Create `voice_gateway/conversation/__init__.py` (empty).

Create `voice_gateway/conversation/session.py`:

```python
"""Conversation session state management."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Session:
    shop_id: UUID
    shop_config: dict
    session_id: UUID = field(default_factory=uuid4)
    system_prompt: str = ""
    customer: dict | None = None
    caller_phone: str | None = None
    history: list[dict] = field(default_factory=list)
    max_history: int = 20
    # Populated after session start with shop's service/staff lists
    _services: list[str] = field(default_factory=list)
    _staff: list[str] = field(default_factory=list)
    _services_list: list[dict] = field(default_factory=list)
    _staff_list: list[dict] = field(default_factory=list)

    def add_user_turn(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})
        self._trim_history()

    def add_assistant_turn(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})
        self._trim_history()

    def _trim_history(self) -> None:
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def format_for_llm(self) -> list[dict]:
        """Return history formatted for LLM conversation."""
        return [{"role": "system", "content": self.system_prompt}] + self.history


class SessionManager:
    """In-memory session registry."""

    def __init__(self):
        self._sessions: dict[UUID, Session] = {}

    def create_session(
        self, shop_id: UUID, shop_config: dict,
        system_prompt: str = "", caller_phone: str | None = None,
    ) -> UUID:
        session = Session(
            shop_id=shop_id, shop_config=shop_config,
            system_prompt=system_prompt, caller_phone=caller_phone,
        )
        self._sessions[session.session_id] = session
        return session.session_id

    def get_session(self, session_id: UUID) -> Session | None:
        return self._sessions.get(session_id)

    def end_session(self, session_id: UUID) -> None:
        self._sessions.pop(session_id, None)
```

- [ ] **Step 4: Write prompt assembler tests**

Create `tests/voice_gateway/test_prompt_assembler.py`:

```python
from voice_gateway.conversation.prompt_assembler import assemble_system_prompt


def test_assembles_full_prompt():
    config = {
        "name": "Salon Bella",
        "personality": "Sei Bella, solare e cordiale.",
        "tone_instructions": "Amichevole, dai del tu",
        "special_instructions": "Suggerisci servizi simili",
    }
    prompt = assemble_system_prompt(config)
    assert "Salon Bella" in prompt
    assert "Sei Bella" in prompt
    assert "Amichevole" in prompt
    assert "Suggerisci servizi simili" in prompt
    assert "italiano" in prompt.lower()


def test_handles_missing_fields():
    config = {"name": "Test Shop"}
    prompt = assemble_system_prompt(config)
    assert "Test Shop" in prompt
    assert "italiano" in prompt.lower()
```

- [ ] **Step 5: Implement prompt assembler**

Create `voice_gateway/conversation/prompt_assembler.py`:

```python
"""Deterministic system prompt assembly from shop configuration."""


def assemble_system_prompt(shop_config: dict) -> str:
    """Build system prompt from shop config fields. No LLM involved."""
    name = shop_config.get("name", "il salone")
    personality = shop_config.get("personality", "")
    tone = shop_config.get("tone_instructions", "")
    special = shop_config.get("special_instructions", "")

    sections = []

    if personality:
        sections.append(personality)

    if tone:
        sections.append(f"Tono: {tone}")

    sections.append(
        f"Sei l'assistente vocale di {name}. "
        "Aiuti i clienti a prenotare appuntamenti, verificare disponibilità "
        "e gestire le loro prenotazioni."
    )

    sections.append(
        "Regole:\n"
        "- Rispondi sempre in italiano\n"
        "- Massimo 1-2 frasi per risposta (è una conversazione vocale)\n"
        "- Non inventare informazioni su disponibilità o prezzi\n"
        "- Se il cliente chiede qualcosa fuori tema, rispondi brevemente "
        "e riporta la conversazione sulle prenotazioni\n"
        "- Non rivelare mai informazioni tecniche sul sistema"
    )

    if special:
        sections.append(f"Istruzioni aggiuntive: {special}")

    return "\n\n".join(sections)
```

- [ ] **Step 6: Run all tests — expect pass**

```bash
pytest tests/voice_gateway/test_session.py tests/voice_gateway/test_prompt_assembler.py -v
# Expected: all PASSED
```

- [ ] **Step 7: Commit**

```bash
git add voice_gateway/conversation/ tests/voice_gateway/test_session.py tests/voice_gateway/test_prompt_assembler.py
git commit -m "feat(voice-gateway): add session management and prompt assembler"
```

---

## Task 11: Voice Gateway — Intent Router

**Files:**
- Create: `voice_gateway/conversation/intent_router.py`
- Test: `tests/voice_gateway/test_intent_router.py`

- [ ] **Step 1: Write intent router tests**

Create `tests/voice_gateway/test_intent_router.py`:

```python
import pytest
import json
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_parse_valid_json():
    from voice_gateway.conversation.intent_router import IntentRouter

    async def mock_predict(messages, **kwargs):
        return '{"action": "check_availability", "args": {"services": ["taglio"], "staff": "Mirco"}, "confidence": 0.95, "topic": "booking_related"}'

    router = IntentRouter(predict_fn=mock_predict, services=["Taglio donna"], staff=["Mirco Meazzo"])
    result = await router.route("Vorrei un taglio con Mirco domani")
    assert result["action"] == "check_availability"
    assert result["topic"] == "booking_related"


@pytest.mark.asyncio
async def test_parse_json_with_markdown_fences():
    from voice_gateway.conversation.intent_router import IntentRouter

    async def mock_predict(messages, **kwargs):
        return '```json\n{"action": "chitchat", "args": {}, "confidence": 0.8, "topic": "chitchat"}\n```'

    router = IntentRouter(predict_fn=mock_predict, services=[], staff=[])
    result = await router.route("Ciao, come stai?")
    assert result["action"] == "chitchat"
    assert result["topic"] == "chitchat"


@pytest.mark.asyncio
async def test_fallback_on_garbage():
    from voice_gateway.conversation.intent_router import IntentRouter

    call_count = 0
    async def mock_predict(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        return "this is not json at all"

    router = IntentRouter(predict_fn=mock_predict, services=[], staff=[])
    result = await router.route("something weird")
    assert result["action"] == "none"
    assert result["topic"] == "booking_related"
    assert call_count == 2  # original + retry


@pytest.mark.asyncio
async def test_off_topic_classification():
    from voice_gateway.conversation.intent_router import IntentRouter

    async def mock_predict(messages, **kwargs):
        return '{"action": "off_topic", "args": {}, "confidence": 0.99, "topic": "off_topic"}'

    router = IntentRouter(predict_fn=mock_predict, services=[], staff=[])
    result = await router.route("Cosa ne pensi delle elezioni?")
    assert result["topic"] == "off_topic"
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/voice_gateway/test_intent_router.py -v
```

- [ ] **Step 3: Implement intent router**

Create `voice_gateway/conversation/intent_router.py`:

```python
"""Intent extraction and guardrail classification via small LLM."""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Awaitable


# Fallback when all parsing fails
_FALLBACK = {"action": "none", "args": {}, "confidence": 0.0, "topic": "booking_related"}

_ACTIONS = [
    "check_availability", "book", "cancel", "reschedule",
    "list_appointments", "ask_service_info", "provide_name",
    "chitchat", "off_topic", "none",
]


class IntentRouter:
    """Routes user text to structured intent via a small/fast LLM."""

    def __init__(
        self,
        predict_fn: Callable[[list[dict], Any], Awaitable[str]],
        services: list[str],
        staff: list[str],
    ):
        self._predict = predict_fn
        self._services = services
        self._staff = staff

    async def route(self, user_text: str) -> dict:
        """Extract intent from user text. Returns dict with action, args, confidence, topic."""
        prompt = self._build_prompt(user_text)
        messages = [{"role": "user", "content": prompt}]

        raw = await self._predict(messages, temperature=0, max_tokens=200)
        result = self._parse_json(raw)
        if result:
            return result

        # Retry with stricter prompt
        retry_prompt = (
            f"Il tuo output precedente non era JSON valido. "
            f"Rispondi SOLO con un oggetto JSON valido per questo messaggio: \"{user_text}\"\n"
            f"Formato: {{\"action\": \"...\", \"args\": {{}}, \"confidence\": 0.0, \"topic\": \"...\"}}"
        )
        raw = await self._predict([{"role": "user", "content": retry_prompt}], temperature=0, max_tokens=200)
        result = self._parse_json(raw)
        return result or _FALLBACK

    def _build_prompt(self, user_text: str) -> str:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        services_str = ", ".join(self._services) if self._services else "nessuno caricato"
        staff_str = ", ".join(self._staff) if self._staff else "nessuno caricato"

        return (
            "Sei un classificatore di intenti per un salone di parrucchieri.\n"
            f"Servizi disponibili: {services_str}\n"
            f"Staff disponibile: {staff_str}\n"
            f"Data e ora corrente: {now}\n\n"
            "Classifica il messaggio del cliente e estrai i parametri.\n"
            f"Azioni possibili: {', '.join(_ACTIONS)}\n"
            "Topic possibili: booking_related, chitchat, off_topic\n\n"
            "Rispondi SOLO con un oggetto JSON valido con questa struttura:\n"
            '{"action": "...", "args": {...}, "confidence": 0.0-1.0, "topic": "..."}\n\n'
            "Per check_availability args deve avere: services (lista nomi), date (YYYY-MM-DD), staff (nome, opzionale)\n"
            "Per book args deve avere: staff_id, service_ids, start_time\n"
            "Per provide_name args deve avere: name\n\n"
            f'Messaggio del cliente: "{user_text}"'
        )

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        """Try to parse JSON from LLM output, handling common issues."""
        text = raw.strip()

        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "action" in data:
                return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        match = re.search(r"\{[^{}]*\}", text)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, dict) and "action" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/voice_gateway/test_intent_router.py -v
# Expected: all PASSED
```

- [ ] **Step 5: Commit**

```bash
git add voice_gateway/conversation/intent_router.py tests/voice_gateway/test_intent_router.py
git commit -m "feat(voice-gateway): add intent router with JSON repair and guardrail classification"
```

---

## Task 12: Voice Gateway — Response Composer

**Files:**
- Create: `voice_gateway/conversation/response_composer.py`
- Test: `tests/voice_gateway/test_response_composer.py`

- [ ] **Step 1: Write response composer tests**

Create `tests/voice_gateway/test_response_composer.py`:

```python
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_compose_booking_response():
    from voice_gateway.conversation.response_composer import ResponseComposer

    async def mock_predict(messages, **kwargs):
        return "Mirco è disponibile domani alle 14 o alle 16:30. Quale preferisci?"

    composer = ResponseComposer(predict_fn=mock_predict)
    result = await composer.compose(
        system_prompt="Sei l'assistente di Salon Bella.",
        history=[{"role": "user", "content": "Vorrei un taglio con Mirco domani"}],
        action="check_availability",
        action_result={"slots": [{"staff_name": "Mirco", "slot_start": "2026-03-30T14:00", "slot_end": "2026-03-30T14:45"}]},
    )
    assert "Mirco" in result


@pytest.mark.asyncio
async def test_compose_chitchat_response():
    from voice_gateway.conversation.response_composer import ResponseComposer

    async def mock_predict(messages, **kwargs):
        return "Bene grazie! Come posso aiutarti oggi?"

    composer = ResponseComposer(predict_fn=mock_predict)
    result = await composer.compose(
        system_prompt="Sei l'assistente.",
        history=[{"role": "user", "content": "Ciao come stai?"}],
        action="chitchat",
        action_result=None,
    )
    assert "grazie" in result.lower()


@pytest.mark.asyncio
async def test_compose_off_topic_static():
    from voice_gateway.conversation.response_composer import ResponseComposer

    composer = ResponseComposer(predict_fn=AsyncMock())
    result = await composer.compose(
        system_prompt="", history=[], action="off_topic", action_result=None,
    )
    assert "prenotazioni" in result.lower() or "capelli" in result.lower()
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/voice_gateway/test_response_composer.py -v
```

- [ ] **Step 3: Implement response composer**

Create `voice_gateway/conversation/response_composer.py`:

```python
"""Natural Italian response generation via large LLM."""
from __future__ import annotations

import json
from typing import Any, Callable, Awaitable

_OFF_TOPIC_RESPONSE = "Mi occupo solo di prenotazioni e servizi per capelli. Posso aiutarti con un appuntamento?"

_NONE_RESPONSE = "Non ho capito bene, puoi ripetere?"


class ResponseComposer:
    """Generates natural Italian conversational responses."""

    def __init__(self, predict_fn: Callable[[list[dict], Any], Awaitable[str]]):
        self._predict = predict_fn

    async def compose(
        self,
        system_prompt: str,
        history: list[dict],
        action: str,
        action_result: dict | None,
    ) -> str:
        # Static responses for guardrails
        if action == "off_topic":
            return _OFF_TOPIC_RESPONSE
        if action == "none":
            return _NONE_RESPONSE

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)

        # Add context about what happened
        if action_result is not None:
            context = (
                f"[Risultato azione '{action}': {json.dumps(action_result, default=str, ensure_ascii=False)}]\n"
                "Rispondi al cliente in modo naturale, massimo 1-2 frasi."
            )
        else:
            context = (
                f"[Azione: {action}. Nessun dato aggiuntivo.]\n"
                "Rispondi al cliente in modo naturale, massimo 1-2 frasi."
            )

        messages.append({"role": "system", "content": context})

        return await self._predict(messages, temperature=0.7, max_tokens=150)
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/voice_gateway/test_response_composer.py -v
# Expected: all PASSED
```

- [ ] **Step 5: Commit**

```bash
git add voice_gateway/conversation/response_composer.py tests/voice_gateway/test_response_composer.py
git commit -m "feat(voice-gateway): add response composer with static guardrail responses"
```

---

## Task 13: Voice Gateway — STT & TTS Clients

**Files:**
- Create: `voice_gateway/voice/__init__.py`
- Create: `voice_gateway/voice/stt.py`
- Create: `voice_gateway/voice/tts.py`

- [ ] **Step 1: Implement STT client**

Create `voice_gateway/voice/__init__.py` (empty).

Create `voice_gateway/voice/stt.py`:

```python
"""Speech-to-Text client for Databricks-hosted Whisper endpoint."""
from __future__ import annotations

import base64
import httpx


class STTClient:
    """Calls a Databricks Model Serving endpoint for Whisper STT."""

    def __init__(self, host: str, token: str, endpoint: str):
        self._url = f"{host.rstrip('/')}/serving-endpoints/{endpoint}/invocations"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def transcribe(self, audio_base64: str) -> str:
        """Send base64-encoded audio to Whisper endpoint, return text."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url,
                headers=self._headers,
                json={"audio": audio_base64, "language": "it"},
            )
            resp.raise_for_status()
            data = resp.json()
            # Handle various response shapes from model serving
            if isinstance(data, dict):
                return data.get("text", data.get("transcription", ""))
            return str(data)
```

- [ ] **Step 2: Implement TTS client**

Create `voice_gateway/voice/tts.py`:

```python
"""Text-to-Speech client for Databricks-hosted Kokoro endpoint."""
from __future__ import annotations

import httpx


class TTSClient:
    """Calls a Databricks Model Serving endpoint for Kokoro TTS."""

    def __init__(self, host: str, token: str, endpoint: str, voice: str = "af_sky"):
        self._url = f"{host.rstrip('/')}/serving-endpoints/{endpoint}/invocations"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._voice = voice

    async def synthesize(self, text: str) -> str:
        """Convert text to speech. Returns base64-encoded audio."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                self._url,
                headers=self._headers,
                json={"text": text, "voice": self._voice, "language": "it"},
            )
            resp.raise_for_status()
            data = resp.json()
            # Extract audio from various response shapes
            if isinstance(data, dict):
                for key in ("audio", "audio_base64", "predictions", "result"):
                    if key in data:
                        val = data[key]
                        if isinstance(val, str):
                            return val
                        if isinstance(val, list) and val:
                            return val[0] if isinstance(val[0], str) else str(val[0])
            return ""
```

- [ ] **Step 3: Commit**

```bash
git add voice_gateway/voice/
git commit -m "feat(voice-gateway): add STT and TTS Databricks endpoint clients"
```

---

## Task 14: Voice Gateway — API Routes (Conversations)

**Files:**
- Create: `voice_gateway/api/__init__.py`
- Create: `voice_gateway/api/app.py`
- Create: `voice_gateway/api/models.py`
- Create: `voice_gateway/api/routes/__init__.py`
- Create: `voice_gateway/api/routes/conversations.py`
- Create: `voice_gateway/api/routes/ws.py`
- Test: `tests/voice_gateway/test_routes_conversations.py`

- [ ] **Step 1: Write conversation route tests**

Create `tests/voice_gateway/test_routes_conversations.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID, uuid4

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")

MOCK_SHOP = {
    "id": str(SHOP_A), "name": "Salon Bella", "welcome_message": "Ciao!",
    "tone_instructions": "friendly", "personality": "sunny",
    "special_instructions": None, "is_active": True,
}


@pytest.fixture
def app():
    from voice_gateway.api.app import create_app
    application = create_app()
    # Mock all external dependencies
    application.state.booking_client = AsyncMock()
    application.state.booking_client.get_shop = AsyncMock(return_value=MOCK_SHOP)
    application.state.booking_client.get_services = AsyncMock(return_value=[])
    application.state.booking_client.get_staff = AsyncMock(return_value=[])
    application.state.booking_client.find_customers_by_phone = AsyncMock(return_value=[])
    application.state.stt = None
    application.state.tts = None
    application.state.intent_predict = AsyncMock(return_value='{"action": "chitchat", "args": {}, "confidence": 0.9, "topic": "chitchat"}')
    application.state.response_predict = AsyncMock(return_value="Bene grazie! Come posso aiutarti?")
    return application


@pytest.mark.asyncio
async def test_start_conversation(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "greeting_text" in data


@pytest.mark.asyncio
async def test_turn_with_text(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Start session
        start_resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
        session_id = start_resp.json()["session_id"]

        # Send turn
        resp = await client.post(
            f"/conversations/{session_id}/turn",
            json={"text": "Ciao, come stai?"},
        )
    assert resp.status_code == 200
    assert "response_text" in resp.json()


@pytest.mark.asyncio
async def test_end_conversation(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start_resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
        session_id = start_resp.json()["session_id"]

        resp = await client.delete(f"/conversations/{session_id}")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests — expect fail**

```bash
pytest tests/voice_gateway/test_routes_conversations.py -v
```

- [ ] **Step 3: Implement Pydantic models**

Create `voice_gateway/api/__init__.py` (empty).

Create `voice_gateway/api/models.py`:

```python
"""Pydantic models for Voice Gateway API."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class StartConversationRequest(BaseModel):
    shop_id: UUID
    caller_phone: str | None = None


class StartConversationResponse(BaseModel):
    session_id: UUID
    greeting_text: str
    greeting_audio: str | None = None


class TurnRequest(BaseModel):
    text: str | None = None
    audio_base64: str | None = None


class TurnResponse(BaseModel):
    response_text: str
    response_audio: str | None = None
    action_taken: str | None = None


class EndConversationResponse(BaseModel):
    session_id: UUID
    farewell: str
```

- [ ] **Step 4: Implement the app factory**

Create `voice_gateway/api/app.py`:

```python
"""Voice Gateway FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from voice_gateway.conversation.session import SessionManager


def create_app() -> FastAPI:
    app = FastAPI(title="Hair Salon Voice Gateway", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    app.state.session_manager = SessionManager()

    from voice_gateway.api.routes import conversations, ws
    app.include_router(conversations.router)
    app.include_router(ws.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
```

- [ ] **Step 5: Implement conversation routes**

Create `voice_gateway/api/routes/__init__.py` (empty).

Create `voice_gateway/api/routes/conversations.py`:

```python
"""Conversation lifecycle routes: start, turn, end."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from voice_gateway.api.models import (
    StartConversationRequest, StartConversationResponse,
    TurnRequest, TurnResponse, EndConversationResponse,
)
from voice_gateway.conversation.prompt_assembler import assemble_system_prompt
from voice_gateway.conversation.intent_router import IntentRouter
from voice_gateway.conversation.response_composer import ResponseComposer

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(body: StartConversationRequest, request: Request):
    app = request.app
    booking = app.state.booking_client

    # Load shop config
    shop = await booking.get_shop(body.shop_id)
    if not shop:
        return JSONResponse(status_code=404, content={"error": "shop_not_found", "message": "Shop not found"})

    # Build system prompt
    system_prompt = assemble_system_prompt(shop)

    # Load services & staff for intent router
    services = await booking.get_services(body.shop_id)
    staff = await booking.get_staff(body.shop_id)

    # Create session
    mgr = app.state.session_manager
    session_id = mgr.create_session(
        shop_id=body.shop_id,
        shop_config=shop,
        system_prompt=system_prompt,
        caller_phone=body.caller_phone,
    )

    session = mgr.get_session(session_id)
    # Store resolved lists on session for intent routing
    session._services[:] = [s.get("service_name", "") for s in services]
    session._staff[:] = [s.get("full_name", "") for s in staff]
    session._staff_list[:] = staff
    session._services_list[:] = services

    # Greeting
    greeting = shop.get("welcome_message", f"Ciao, benvenuto! Come ti chiami?")
    session.add_assistant_turn(greeting)

    # TTS for greeting (optional)
    greeting_audio = None
    if app.state.tts:
        greeting_audio = await app.state.tts.synthesize(greeting)

    return StartConversationResponse(
        session_id=session_id,
        greeting_text=greeting,
        greeting_audio=greeting_audio,
    )


@router.post("/{session_id}/turn", response_model=TurnResponse)
async def process_turn(session_id: UUID, body: TurnRequest, request: Request):
    app = request.app
    mgr = app.state.session_manager
    session = mgr.get_session(session_id)

    if not session:
        return JSONResponse(status_code=404, content={"error": "session_not_found", "message": "Session not found"})

    # Get user text: from direct text or STT
    user_text = body.text
    if not user_text and body.audio_base64 and app.state.stt:
        user_text = await app.state.stt.transcribe(body.audio_base64)
    if not user_text:
        return JSONResponse(status_code=400, content={"error": "no_input", "message": "Provide text or audio_base64"})

    session.add_user_turn(user_text)

    # Intent routing
    intent_router = IntentRouter(
        predict_fn=app.state.intent_predict,
        services=getattr(session, "_services", []),
        staff=getattr(session, "_staff", []),
    )
    intent = await intent_router.route(user_text)
    action = intent.get("action", "none")
    args = intent.get("args", {})
    topic = intent.get("topic", "booking_related")

    # Handle customer identification
    if action == "provide_name":
        name = args.get("name", "")
        action_result = await _identify_customer(app, session, name)

    # Execute action against Booking Engine if needed
    elif topic == "booking_related" and action not in ("none", "chitchat", "off_topic"):
        action_result = await _execute_action(app, session, action, args)

    # Compose response
    composer = ResponseComposer(predict_fn=app.state.response_predict)
    response_text = await composer.compose(
        system_prompt=session.system_prompt,
        history=session.history,
        action=action,
        action_result=action_result,
    )

    session.add_assistant_turn(response_text)

    # TTS (optional)
    response_audio = None
    if app.state.tts:
        response_audio = await app.state.tts.synthesize(response_text)

    return TurnResponse(
        response_text=response_text,
        response_audio=response_audio,
        action_taken=action,
    )


@router.delete("/{session_id}", response_model=EndConversationResponse)
async def end_conversation(session_id: UUID, request: Request):
    mgr = request.app.state.session_manager
    session = mgr.get_session(session_id)

    if not session:
        return JSONResponse(status_code=404, content={"error": "session_not_found", "message": "Session not found"})

    farewell = "Grazie per aver chiamato, a presto!"
    mgr.end_session(session_id)

    return EndConversationResponse(session_id=session_id, farewell=farewell)


async def _execute_action(app, session, action: str, args: dict) -> dict | None:
    """Dispatch action to Booking Engine and return result."""
    booking = app.state.booking_client
    shop_id = session.shop_id

    try:
        if action == "check_availability":
            # Resolve service names to IDs
            service_names = args.get("services", [])
            service_ids = _resolve_service_ids(service_names, getattr(session, "_services_list", []))
            if not service_ids:
                return {"error": "No matching services found"}

            staff_id = _resolve_staff_id(args.get("staff"), getattr(session, "_staff_list", []))
            date_str = args.get("date", args.get("start_date"))

            if date_str:
                from datetime import date as d
                start = d.fromisoformat(date_str)
                end = args.get("end_date", date_str)
                end = d.fromisoformat(end) if isinstance(end, str) else start
            else:
                from datetime import date as d, timedelta
                start = d.today()
                end = start + timedelta(days=3)

            return await booking.check_availability(shop_id, service_ids, start, end, staff_id)

        elif action == "book":
            return await booking.book_appointment(
                shop_id=shop_id,
                customer_id=UUID(args["customer_id"]),
                service_ids=[UUID(s) for s in args["service_ids"]],
                staff_id=UUID(args["staff_id"]),
                start_time=args["start_time"],
            )

        elif action == "cancel":
            return await booking.cancel_appointment(shop_id, UUID(args["appointment_id"]))

        elif action == "reschedule":
            return await booking.reschedule_appointment(
                shop_id, UUID(args["appointment_id"]),
                args["new_start_time"], args.get("new_staff_id"),
            )

        elif action == "list_appointments":
            if session.customer:
                return await booking.list_appointments(shop_id, UUID(session.customer["id"]))
            return {"error": "Customer not identified yet"}

        elif action == "ask_service_info":
            return {"services": getattr(session, "_services_list", [])}

    except Exception as e:
        return {"error": str(e)}

    return None


async def _identify_customer(app, session, name: str) -> dict:
    """Handle customer identification flow per spec:
    1. If caller_phone provided, search by phone in this shop
    2. Match name (case-insensitive first-name prefix)
    3. If multiple matches, return disambiguation list
    4. If no match, create new customer + link phone
    5. Ambiguity guard: skip phone linking if 5+ linked customers and no match
    """
    booking = app.state.booking_client
    shop_id = session.shop_id
    phone = session.caller_phone

    if phone:
        # Get all customers linked to this phone
        phone_customers = await booking.find_customers_by_phone(shop_id, phone)

        # Ambiguity guard: too many linked customers, skip phone matching
        if len(phone_customers) >= 5:
            customer = await booking.create_customer(shop_id, name)
            session.customer = customer
            return {"identified": True, "new_customer": True, "name": name}

        # Try name+phone match
        matches = await booking.find_customer_by_name_phone(shop_id, name, phone)

        if len(matches) == 1:
            session.customer = matches[0]
            return {"identified": True, "name": matches[0].get("full_name", name)}

        if len(matches) > 1:
            names = [m.get("full_name", "") for m in matches]
            return {"identified": False, "disambiguation": names,
                    "message": f"Abbiamo più clienti con quel nome. Sei {' o '.join(names)}?"}

    # No phone or no match: create new customer
    customer = await booking.create_customer(shop_id, name, phone)
    session.customer = customer
    return {"identified": True, "new_customer": True, "name": name}


def _resolve_service_ids(names: list[str], services: list[dict]) -> list:
    """Match service names to IDs (case-insensitive partial match)."""
    from uuid import UUID
    result = []
    for name in names:
        name_lower = name.lower()
        for svc in services:
            if name_lower in svc.get("service_name", "").lower():
                result.append(UUID(svc["id"]) if isinstance(svc["id"], str) else svc["id"])
                break
    return result


def _resolve_staff_id(name: str | None, staff: list[dict]):
    """Match staff name to ID (case-insensitive partial match)."""
    if not name:
        return None
    from uuid import UUID
    name_lower = name.lower()
    for s in staff:
        if name_lower in s.get("full_name", "").lower():
            return UUID(s["id"]) if isinstance(s["id"], str) else s["id"]
    return None
```

- [ ] **Step 6: Create WebSocket scaffold**

Create `voice_gateway/api/routes/ws.py`:

```python
"""WebSocket streaming endpoint — scaffold for future telephony integration."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/conversations/{session_id}/stream")
async def stream_conversation(websocket: WebSocket, session_id: str):
    """Bidirectional audio streaming. Not yet implemented for MVP.

    Future: telephony adapter pipes audio chunks here.
    Server sends back audio response frames.
    """
    await websocket.accept()
    try:
        await websocket.send_json({
            "type": "error",
            "message": "WebSocket streaming not yet implemented. Use REST /turn endpoint for MVP.",
        })
        await websocket.close()
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 7: Run tests — expect pass**

```bash
pytest tests/voice_gateway/test_routes_conversations.py -v
# Expected: all PASSED
```

- [ ] **Step 8: Commit**

```bash
git add voice_gateway/api/ tests/voice_gateway/test_routes_conversations.py
git commit -m "feat(voice-gateway): add conversation API routes with intent routing and response composition"
```

---

## Task 15: Voice Gateway — Databricks App Config & LLM Predict Functions

**Files:**
- Create: `voice_gateway/app.yaml`
- Create: `voice_gateway/llm.py`

- [ ] **Step 1: Create LLM predict functions**

Create `voice_gateway/llm.py`:

```python
"""LLM predict functions for Databricks Model Serving endpoints."""
from __future__ import annotations

from typing import Any

import httpx


def make_predict_fn(host: str, token: str, endpoint: str):
    """Create an async predict function for a Databricks Model Serving endpoint."""
    url = f"{host.rstrip('/')}/serving-endpoints/{endpoint}/invocations"
    headers = {"Authorization": f"Bearer {token}"}

    async def predict(messages: list[dict], temperature: float = 0.0, max_tokens: int = 200, **kwargs) -> str:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Standard chat completion response
            if "choices" in data and data["choices"]:
                return data["choices"][0].get("message", {}).get("content", "")
            # Direct content
            if "content" in data:
                return data["content"]
            return str(data)

    return predict
```

- [ ] **Step 2: Create app.yaml**

Create `voice_gateway/app.yaml`:

```yaml
command:
  - uvicorn
  - voice_gateway.api.app:create_app
  - --host=0.0.0.0
  - --port=8001
  - --factory

env:
  - name: BOOKING_ENGINE_URL
    description: Base URL of the Booking Engine service
  - name: DATABRICKS_HOST
    description: Databricks workspace URL
  - name: DATABRICKS_TOKEN
    description: Databricks PAT or OAuth token
  - name: STT_ENDPOINT
    value: "whisper-stt-endpoint"
  - name: TTS_ENDPOINT
    value: "kokoro-tts-endpoint"
  - name: INTENT_LLM_ENDPOINT
    value: "databricks-meta-llama-3-1-8b-instruct"
  - name: RESPONSE_LLM_ENDPOINT
    value: "databricks-meta-llama-3-3-70b-instruct"
```

- [ ] **Step 3: Commit**

```bash
git add voice_gateway/llm.py voice_gateway/app.yaml
git commit -m "feat(voice-gateway): add LLM predict functions and Databricks App config"
```

---

## Task 16: Integration — Wire Up Startup & End-to-End Text Test

**Files:**
- Modify: `voice_gateway/api/app.py` (add startup wiring)
- Create: `tests/test_e2e_text.py`

- [ ] **Step 1: Update Voice Gateway app with production startup**

Add lifespan to `voice_gateway/api/app.py` that wires real clients:

```python
# Add at the top of create_app(), before router includes:

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up real clients from env vars if available."""
    import os
    from voice_gateway.config import Settings

    try:
        settings = Settings()
        from voice_gateway.clients.booking_client import BookingClient
        bc = BookingClient(base_url=settings.booking_engine_url)
        await bc.__aenter__()
        app.state.booking_client = bc

        from voice_gateway.voice.stt import STTClient
        from voice_gateway.voice.tts import TTSClient
        app.state.stt = STTClient(settings.databricks_host, settings.databricks_token, settings.stt_endpoint)
        app.state.tts = TTSClient(settings.databricks_host, settings.databricks_token, settings.tts_endpoint)

        from voice_gateway.llm import make_predict_fn
        app.state.intent_predict = make_predict_fn(settings.databricks_host, settings.databricks_token, settings.intent_llm_endpoint)
        app.state.response_predict = make_predict_fn(settings.databricks_host, settings.databricks_token, settings.response_llm_endpoint)
    except Exception:
        # Allow app to start without env vars (for testing)
        pass

    yield

    if hasattr(app.state, 'booking_client') and app.state.booking_client:
        await app.state.booking_client.__aexit__(None, None, None)
```

Then pass `lifespan=lifespan` to the `FastAPI()` constructor.

- [ ] **Step 2: Write E2E text test**

Create `tests/test_e2e_text.py`:

```python
"""End-to-end test using text-only mode (no STT/TTS, mocked Booking Engine + LLMs)."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from uuid import UUID

SHOP_A = UUID("a0000000-0000-0000-0000-000000000001")

MOCK_SHOP = {
    "id": str(SHOP_A), "name": "Salon Bella",
    "welcome_message": "Ciao, benvenuto da Salon Bella! Come ti chiami?",
    "tone_instructions": "Amichevole", "personality": "Sei Bella, solare.",
    "special_instructions": None, "is_active": True,
    "phone_number": None, "address": None,
}

MOCK_SERVICES = [
    {"id": "aaaa0001-0000-0000-0000-000000000001", "service_name": "Taglio donna", "duration_minutes": 45},
]

MOCK_STAFF = [
    {"id": "11111111-0000-0000-0000-000000000001", "full_name": "Mirco Meazzo"},
]


@pytest.fixture
def app():
    from voice_gateway.api.app import create_app
    application = create_app()

    # Mock booking client
    bc = AsyncMock()
    bc.get_shop = AsyncMock(return_value=MOCK_SHOP)
    bc.get_services = AsyncMock(return_value=MOCK_SERVICES)
    bc.get_staff = AsyncMock(return_value=MOCK_STAFF)
    bc.find_customers_by_phone = AsyncMock(return_value=[])
    bc.check_availability = AsyncMock(return_value={
        "slots": [{"staff_id": "11111111-0000-0000-0000-000000000001", "staff_name": "Mirco", "slot_start": "2026-03-30T14:00", "slot_end": "2026-03-30T14:45"}],
        "suggestions": None,
    })
    application.state.booking_client = bc

    # Mock LLMs
    application.state.intent_predict = AsyncMock(side_effect=[
        # Turn 1: provide name
        '{"action": "provide_name", "args": {"name": "Maria"}, "confidence": 0.95, "topic": "booking_related"}',
        # Turn 2: check availability
        '{"action": "check_availability", "args": {"services": ["taglio"], "staff": "Mirco", "date": "2026-03-30"}, "confidence": 0.95, "topic": "booking_related"}',
    ])
    application.state.response_predict = AsyncMock(side_effect=[
        "Ciao Maria! Come posso aiutarti?",
        "Mirco è disponibile domani alle 14. Vuoi prenotare?",
    ])

    application.state.stt = None
    application.state.tts = None

    return application


@pytest.mark.asyncio
async def test_full_conversation_flow(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Start
        resp = await client.post("/conversations/start", json={"shop_id": str(SHOP_A)})
        assert resp.status_code == 200
        data = resp.json()
        session_id = data["session_id"]
        assert "Salon Bella" in data["greeting_text"]

        # Turn 1: provide name
        resp = await client.post(f"/conversations/{session_id}/turn", json={"text": "Sono Maria"})
        assert resp.status_code == 200
        assert "Maria" in resp.json()["response_text"]

        # Turn 2: check availability
        resp = await client.post(
            f"/conversations/{session_id}/turn",
            json={"text": "Vorrei un taglio con Mirco domani"},
        )
        assert resp.status_code == 200
        assert "Mirco" in resp.json()["response_text"]

        # End
        resp = await client.delete(f"/conversations/{session_id}")
        assert resp.status_code == 200
```

- [ ] **Step 3: Run E2E test — expect pass**

```bash
pytest tests/test_e2e_text.py -v
# Expected: PASSED
```

- [ ] **Step 4: Commit**

```bash
git add voice_gateway/api/app.py tests/test_e2e_text.py
git commit -m "feat: wire up startup lifecycle and add E2E text conversation test"
```

---

## Task 17: Final — Run All Tests & Verify

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
# Expected: all tests PASSED
```

- [ ] **Step 2: Verify project structure**

```bash
find . -name "*.py" -not -path "./.git/*" -not -path "./.venv/*" | sort
# Verify matches the file map at the top of this plan
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: verify all tests pass and project structure is clean"
```

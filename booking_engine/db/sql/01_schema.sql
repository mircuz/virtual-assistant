-- Virtual Assistant Booking Engine — Delta Tables Schema
-- Target: mircom_test.virtual_assistant on Databricks SQL
-- Run each statement individually in a Databricks SQL notebook or editor.

-- ============================================================
-- 0. Catalog & Schema
-- ============================================================

CREATE CATALOG IF NOT EXISTS mircom_test;

CREATE SCHEMA IF NOT EXISTS mircom_test.virtual_assistant;

-- Grant access (adjust principal as needed)
GRANT USE CATALOG ON CATALOG mircom_test TO `account users`;
GRANT USE SCHEMA, SELECT, MODIFY ON SCHEMA mircom_test.virtual_assistant TO `account users`;

-- ============================================================
-- 1. Shops
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.shops (
  id                  STRING        NOT NULL,
  name                STRING        NOT NULL,
  phone_number        STRING,
  address             STRING,
  welcome_message     STRING,
  tone_instructions   STRING,
  personality         STRING,
  special_instructions STRING,
  is_active           BOOLEAN       NOT NULL DEFAULT true,
  created_at          TIMESTAMP     NOT NULL DEFAULT current_timestamp()
);

-- ============================================================
-- 2. Staff
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.staff (
  id          STRING        NOT NULL,
  shop_id     STRING        NOT NULL,
  full_name   STRING        NOT NULL,
  role        STRING,
  phone_number STRING,
  email       STRING,
  bio         STRING,
  is_active   BOOLEAN       NOT NULL DEFAULT true,
  created_at  TIMESTAMP     NOT NULL DEFAULT current_timestamp()
);

-- ============================================================
-- 3. Services
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.services (
  id                STRING        NOT NULL,
  shop_id           STRING        NOT NULL,
  service_name      STRING        NOT NULL,
  description       STRING,
  duration_minutes  INT           NOT NULL,
  price_eur         DECIMAL(8,2),
  category          STRING,
  is_active         BOOLEAN       NOT NULL DEFAULT true,
  created_at        TIMESTAMP     NOT NULL DEFAULT current_timestamp()
);

-- ============================================================
-- 4. Staff ↔ Services (M2M)
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.staff_services (
  staff_id    STRING  NOT NULL,
  service_id  STRING  NOT NULL
);

-- ============================================================
-- 5. Staff Schedules
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.staff_schedules (
  id            STRING  NOT NULL,
  staff_id      STRING  NOT NULL,
  day_of_week   INT     NOT NULL,   -- 0=Monday .. 6=Sunday (ISO)
  start_time    STRING  NOT NULL,   -- HH:MM format
  end_time      STRING  NOT NULL    -- HH:MM format
);

-- ============================================================
-- 6. Customers
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.customers (
  id                  STRING        NOT NULL,
  shop_id             STRING        NOT NULL,
  full_name           STRING        NOT NULL,
  email               STRING,
  preferred_staff_id  STRING,
  notes               STRING,
  created_at          TIMESTAMP     NOT NULL DEFAULT current_timestamp()
);

-- ============================================================
-- 7. Phone Contacts (caller ID linking)
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.phone_contacts (
  id            STRING      NOT NULL,
  phone_number  STRING      NOT NULL,
  customer_id   STRING      NOT NULL,
  last_seen_at  TIMESTAMP   NOT NULL DEFAULT current_timestamp()
);

-- ============================================================
-- 8. Appointments
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.appointments (
  id            STRING      NOT NULL,
  shop_id       STRING      NOT NULL,
  customer_id   STRING      NOT NULL,
  staff_id      STRING      NOT NULL,
  start_time    TIMESTAMP   NOT NULL,
  end_time      TIMESTAMP   NOT NULL,
  status        STRING      NOT NULL DEFAULT 'scheduled',
  notes         STRING,
  created_at    TIMESTAMP   NOT NULL DEFAULT current_timestamp()
);

-- ============================================================
-- 9. Appointment ↔ Services (junction)
-- ============================================================

CREATE TABLE IF NOT EXISTS mircom_test.virtual_assistant.appointment_services (
  appointment_id    STRING        NOT NULL,
  service_id        STRING        NOT NULL,
  duration_minutes  INT           NOT NULL,
  price_eur         DECIMAL(8,2)
);

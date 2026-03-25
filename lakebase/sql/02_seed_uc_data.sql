-- =============================================================================
-- Salon Bella Milano — Unity Catalog Seed Data
-- =============================================================================
-- Italian hair salon booking assistant test dataset for catalog mircom_test,
-- schema assistant_mochi. Run in Databricks SQL (Unity Catalog).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS mircom_test.assistant_mochi;

-- -----------------------------------------------------------------------------
-- Drop tables in reverse dependency order for clean re-seeding
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS mircom_test.assistant_mochi.appointments;
DROP TABLE IF EXISTS mircom_test.assistant_mochi.staff_schedules;
DROP TABLE IF EXISTS mircom_test.assistant_mochi.staff_services;
DROP TABLE IF EXISTS mircom_test.assistant_mochi.services;
DROP TABLE IF EXISTS mircom_test.assistant_mochi.seats;
DROP TABLE IF EXISTS mircom_test.assistant_mochi.staff;
DROP TABLE IF EXISTS mircom_test.assistant_mochi.customers;

-- -----------------------------------------------------------------------------
-- customers
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mircom_test.assistant_mochi.customers (
    customer_id STRING,
    full_name STRING,
    phone_number STRING,
    email STRING,
    preferred_language STRING,
    notes STRING,
    created_at TIMESTAMP
)
USING DELTA;

INSERT INTO mircom_test.assistant_mochi.customers VALUES
    ('cust_001', 'Elena Rossi', '+39 333 1234567', 'elena.rossi@email.it', 'it', NULL, TIMESTAMP '2025-01-15 10:00:00'),
    ('cust_002', 'Luca Bianchi', '+39 340 2345678', 'luca.bianchi@email.it', 'it', NULL, TIMESTAMP '2025-02-01 14:30:00'),
    ('cust_003', 'Francesca Verdi', '+39 347 3456789', 'francesca.verdi@email.it', 'it', 'Allergica a alcuni prodotti', TIMESTAMP '2025-02-10 09:15:00'),
    ('cust_004', 'Alessandro Neri', '+39 328 4567890', 'alessandro.neri@email.it', 'it', NULL, TIMESTAMP '2025-02-20 11:00:00'),
    ('cust_005', 'Chiara Colombo', '+39 333 5678901', 'chiara.colombo@email.it', 'it', NULL, TIMESTAMP '2025-03-01 16:45:00');

-- -----------------------------------------------------------------------------
-- staff
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mircom_test.assistant_mochi.staff (
    staff_id STRING,
    full_name STRING,
    role STRING,
    phone_number STRING,
    email STRING,
    bio STRING,
    is_active BOOLEAN,
    created_at TIMESTAMP
)
USING DELTA;

INSERT INTO mircom_test.assistant_mochi.staff VALUES
    ('staff_001', 'Giulia Marinetti', 'senior stilista', '+39 02 1234567', 'giulia.marinetti@salonbella.it', 'Esperta in colorazioni e tagli moderni. 15 anni di esperienza.', TRUE, TIMESTAMP '2024-01-10 08:00:00'),
    ('staff_002', 'Marco Ferretti', 'stilista', '+39 02 2345678', 'marco.ferretti@salonbella.it', 'Specializzato in taglio e piega. Stile classico e contemporaneo.', TRUE, TIMESTAMP '2024-03-15 08:00:00'),
    ('staff_003', 'Sofia Greco', 'colorista', '+39 02 3456789', 'sofia.greco@salonbella.it', 'Colorista certificata. Meches, balayage e trattamenti cheratina.', TRUE, TIMESTAMP '2024-06-01 08:00:00'),
    ('staff_004', 'Anna Ricci', 'assistente', '+39 02 4567890', 'anna.ricci@salonbella.it', 'Assistente di sala. Piega e lavaggio.', TRUE, TIMESTAMP '2024-09-01 08:00:00');

-- -----------------------------------------------------------------------------
-- seats
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mircom_test.assistant_mochi.seats (
    seat_id STRING,
    seat_name STRING,
    seat_type STRING,
    is_active BOOLEAN
)
USING DELTA;

INSERT INTO mircom_test.assistant_mochi.seats VALUES
    ('seat_001', 'Postazione 1', 'standard', TRUE),
    ('seat_002', 'Postazione 2', 'standard', TRUE),
    ('seat_003', 'Postazione 3', 'standard', TRUE),
    ('seat_004', 'Postazione VIP', 'vip', TRUE),
    ('seat_005', 'Lavaggio', 'wash', TRUE);

-- -----------------------------------------------------------------------------
-- services
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mircom_test.assistant_mochi.services (
    service_id STRING,
    service_name STRING,
    description STRING,
    duration_minutes INT,
    price_eur DOUBLE,
    category STRING,
    requires_seat_type STRING,
    is_active BOOLEAN
)
USING DELTA;

INSERT INTO mircom_test.assistant_mochi.services VALUES
    ('svc_001', 'Taglio donna', 'Taglio e rifinitura per capelli lunghi o corti', 45, 35.00, 'taglio', 'standard', TRUE),
    ('svc_002', 'Taglio uomo', 'Taglio classico o moderno per uomo', 30, 22.00, 'taglio', 'standard', TRUE),
    ('svc_003', 'Piega', 'Piega con asciugacapelli e styling', 30, 25.00, 'styling', 'standard', TRUE),
    ('svc_004', 'Colore', 'Colorazione completa o radici', 120, 75.00, 'colore', 'standard', TRUE),
    ('svc_005', 'Meches', 'Meches balayage o highlights', 90, 90.00, 'colore', 'standard', TRUE),
    ('svc_006', 'Trattamento cheratina', 'Trattamento cheratina brasiliana', 90, 80.00, 'trattamento', 'standard', TRUE);

-- -----------------------------------------------------------------------------
-- staff_services
-- Giulia: all 6 | Marco: taglio donna, taglio uomo, piega | Sofia: colore, meches, cheratina, piega | Anna: piega
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mircom_test.assistant_mochi.staff_services (
    staff_id STRING,
    service_id STRING
)
USING DELTA;

INSERT INTO mircom_test.assistant_mochi.staff_services VALUES
    ('staff_001', 'svc_001'),
    ('staff_001', 'svc_002'),
    ('staff_001', 'svc_003'),
    ('staff_001', 'svc_004'),
    ('staff_001', 'svc_005'),
    ('staff_001', 'svc_006'),
    ('staff_002', 'svc_001'),
    ('staff_002', 'svc_002'),
    ('staff_002', 'svc_003'),
    ('staff_003', 'svc_003'),
    ('staff_003', 'svc_004'),
    ('staff_003', 'svc_005'),
    ('staff_003', 'svc_006'),
    ('staff_004', 'svc_003');

-- -----------------------------------------------------------------------------
-- staff_schedules (day_of_week: 1=Mon, 7=Sun)
-- Giulia: Mon-Sat 9-18 | Marco: Tue-Sat 10-19 | Sofia: Mon-Fri 9-17 | Anna: Mon-Sat 9-14
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mircom_test.assistant_mochi.staff_schedules (
    schedule_id STRING,
    staff_id STRING,
    day_of_week INT,
    start_time STRING,
    end_time STRING
)
USING DELTA;

INSERT INTO mircom_test.assistant_mochi.staff_schedules VALUES
    ('sched_001', 'staff_001', 1, '09:00', '18:00'),
    ('sched_002', 'staff_001', 2, '09:00', '18:00'),
    ('sched_003', 'staff_001', 3, '09:00', '18:00'),
    ('sched_004', 'staff_001', 4, '09:00', '18:00'),
    ('sched_005', 'staff_001', 5, '09:00', '18:00'),
    ('sched_006', 'staff_001', 6, '09:00', '18:00'),
    ('sched_007', 'staff_002', 2, '10:00', '19:00'),
    ('sched_008', 'staff_002', 3, '10:00', '19:00'),
    ('sched_009', 'staff_002', 4, '10:00', '19:00'),
    ('sched_010', 'staff_002', 5, '10:00', '19:00'),
    ('sched_011', 'staff_002', 6, '10:00', '19:00'),
    ('sched_012', 'staff_003', 1, '09:00', '17:00'),
    ('sched_013', 'staff_003', 2, '09:00', '17:00'),
    ('sched_014', 'staff_003', 3, '09:00', '17:00'),
    ('sched_015', 'staff_003', 4, '09:00', '17:00'),
    ('sched_016', 'staff_003', 5, '09:00', '17:00'),
    ('sched_017', 'staff_004', 1, '09:00', '14:00'),
    ('sched_018', 'staff_004', 2, '09:00', '14:00'),
    ('sched_019', 'staff_004', 3, '09:00', '14:00'),
    ('sched_020', 'staff_004', 4, '09:00', '14:00'),
    ('sched_021', 'staff_004', 5, '09:00', '14:00'),
    ('sched_022', 'staff_004', 6, '09:00', '14:00');

-- -----------------------------------------------------------------------------
-- appointments (2026-03-06 = Friday; mix of completed, confirmed, scheduled, cancelled)
-- No double-bookings; realistic combinations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mircom_test.assistant_mochi.appointments (
    appointment_id STRING,
    customer_id STRING,
    staff_id STRING,
    seat_id STRING,
    service_id STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status STRING,
    notes STRING,
    booked_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason STRING
)
USING DELTA;

INSERT INTO mircom_test.assistant_mochi.appointments VALUES
    ('appt_001', 'cust_001', 'staff_001', 'seat_001', 'svc_004', TIMESTAMP '2026-03-06 10:00:00', TIMESTAMP '2026-03-06 12:00:00', 'confirmed', 'Colore castano chiaro', TIMESTAMP '2026-03-01 14:22:00', NULL, NULL),
    ('appt_002', 'cust_002', 'staff_002', 'seat_002', 'svc_002', TIMESTAMP '2026-03-06 11:00:00', TIMESTAMP '2026-03-06 11:30:00', 'scheduled', NULL, TIMESTAMP '2026-03-03 09:15:00', NULL, NULL),
    ('appt_003', 'cust_003', 'staff_003', 'seat_003', 'svc_006', TIMESTAMP '2026-03-06 14:00:00', TIMESTAMP '2026-03-06 15:30:00', 'confirmed', 'Prima volta cheratina', TIMESTAMP '2026-03-02 11:30:00', NULL, NULL),
    ('appt_004', 'cust_004', 'staff_004', 'seat_004', 'svc_003', TIMESTAMP '2026-03-06 09:00:00', TIMESTAMP '2026-03-06 09:30:00', 'completed', NULL, TIMESTAMP '2026-03-04 16:00:00', NULL, NULL),
    ('appt_005', 'cust_005', 'staff_002', 'seat_002', 'svc_001', TIMESTAMP '2026-03-06 15:00:00', TIMESTAMP '2026-03-06 15:45:00', 'scheduled', NULL, TIMESTAMP '2026-03-05 10:00:00', NULL, NULL),
    ('appt_006', 'cust_001', 'staff_001', 'seat_003', 'svc_005', TIMESTAMP '2026-03-06 16:00:00', TIMESTAMP '2026-03-06 17:30:00', 'cancelled', NULL, TIMESTAMP '2026-03-02 12:00:00', TIMESTAMP '2026-03-05 18:30:00', 'Cliente ha posticipato per impegni');

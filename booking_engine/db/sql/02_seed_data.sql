-- Virtual Assistant Booking Engine — Seed Data
-- Target: mircom_test.virtual_assistant on Databricks SQL
-- Run after 01_schema.sql. Safe to re-run (uses MERGE to avoid duplicates).

-- ============================================================
-- Shops
-- ============================================================

MERGE INTO mircom_test.virtual_assistant.shops AS t
USING (
  SELECT 'a0000000-0000-0000-0000-000000000001' AS id, 'Salon Bella' AS name,
         '+39 02 1234567' AS phone_number, 'Via Roma 42, Milano' AS address,
         'Ciao, benvenuto da Salon Bella! Come ti chiami?' AS welcome_message,
         'Amichevole e informale, dai del tu al cliente' AS tone_instructions,
         'Sei Bella, l''assistente virtuale del Salon Bella. Sei solare, cordiale e sempre pronta ad aiutare.' AS personality,
         'Se il cliente chiede di un servizio che non offriamo, suggerisci il servizio più simile disponibile.' AS special_instructions
  UNION ALL
  SELECT 'b0000000-0000-0000-0000-000000000002', 'Studio Hair',
         '+39 06 7654321', 'Via del Corso 15, Roma',
         'Buongiorno, benvenuto allo Studio Hair. Come posso aiutarla?',
         'Professionale e formale, dia del lei al cliente',
         'Sei l''assistente dello Studio Hair. Sei professionale, preciso e attento ai dettagli.',
         NULL
) AS s ON t.id = s.id
WHEN NOT MATCHED THEN INSERT (id, name, phone_number, address, welcome_message, tone_instructions, personality, special_instructions, is_active)
VALUES (s.id, s.name, s.phone_number, s.address, s.welcome_message, s.tone_instructions, s.personality, s.special_instructions, true);

-- ============================================================
-- Staff
-- ============================================================

MERGE INTO mircom_test.virtual_assistant.staff AS t
USING (
  SELECT '11111111-0000-0000-0000-000000000001' AS id, 'a0000000-0000-0000-0000-000000000001' AS shop_id, 'Mirco Meazzo' AS full_name, 'stilista senior' AS role, 'Stilista con 15 anni di esperienza' AS bio
  UNION ALL SELECT '11111111-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'Giulia Verdi', 'colorista', 'Esperta di colorazioni e trattamenti'
  UNION ALL SELECT '11111111-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'Marco Bianchi', 'stilista', 'Specializzato in tagli classici e barba'
  UNION ALL SELECT '22222222-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Anna Rossi', 'stilista senior', 'Stilista di fama internazionale'
  UNION ALL SELECT '22222222-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'Luca Neri', 'colorista', 'Esperto di balayage e meches'
) AS s ON t.id = s.id
WHEN NOT MATCHED THEN INSERT (id, shop_id, full_name, role, bio, is_active)
VALUES (s.id, s.shop_id, s.full_name, s.role, s.bio, true);

-- ============================================================
-- Services
-- ============================================================

MERGE INTO mircom_test.virtual_assistant.services AS t
USING (
  -- Salon Bella services
  SELECT 'aaaa0001-0000-0000-0000-000000000001' AS id, 'a0000000-0000-0000-0000-000000000001' AS shop_id, 'Taglio donna' AS service_name, 'Taglio, shampoo e piega' AS description, 45 AS duration_minutes, 35.00 AS price_eur, 'taglio' AS category
  UNION ALL SELECT 'aaaa0001-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'Taglio uomo', 'Taglio maschile classico o moderno', 30, 25.00, 'taglio'
  UNION ALL SELECT 'aaaa0001-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'Colore', 'Colorazione completa', 60, 55.00, 'colore'
  UNION ALL SELECT 'aaaa0001-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', 'Meches', 'Meches o colpi di sole', 90, 70.00, 'colore'
  UNION ALL SELECT 'aaaa0001-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001', 'Piega', 'Piega semplice', 30, 20.00, 'piega'
  UNION ALL SELECT 'aaaa0001-0000-0000-0000-000000000006', 'a0000000-0000-0000-0000-000000000001', 'Trattamento cheratina', 'Trattamento lisciante alla cheratina', 120, 90.00, 'trattamento'
  -- Studio Hair services
  UNION ALL SELECT 'bbbb0001-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Taglio donna', 'Taglio con consulenza personalizzata', 50, 45.00, 'taglio'
  UNION ALL SELECT 'bbbb0001-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'Colore', 'Colorazione premium', 75, 80.00, 'colore'
  UNION ALL SELECT 'bbbb0001-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000002', 'Balayage', 'Balayage naturale', 120, 120.00, 'colore'
  UNION ALL SELECT 'bbbb0001-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000002', 'Piega', 'Piega professionale', 30, 30.00, 'piega'
) AS s ON t.id = s.id
WHEN NOT MATCHED THEN INSERT (id, shop_id, service_name, description, duration_minutes, price_eur, category, is_active)
VALUES (s.id, s.shop_id, s.service_name, s.description, s.duration_minutes, s.price_eur, s.category, true);

-- ============================================================
-- Staff ↔ Services
-- ============================================================

MERGE INTO mircom_test.virtual_assistant.staff_services AS t
USING (
  -- Mirco Meazzo: taglio donna, taglio uomo, piega
  SELECT '11111111-0000-0000-0000-000000000001' AS staff_id, 'aaaa0001-0000-0000-0000-000000000001' AS service_id
  UNION ALL SELECT '11111111-0000-0000-0000-000000000001', 'aaaa0001-0000-0000-0000-000000000002'
  UNION ALL SELECT '11111111-0000-0000-0000-000000000001', 'aaaa0001-0000-0000-0000-000000000005'
  -- Giulia Verdi: colore, meches, piega, cheratina
  UNION ALL SELECT '11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000003'
  UNION ALL SELECT '11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000004'
  UNION ALL SELECT '11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000005'
  UNION ALL SELECT '11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000006'
  -- Marco Bianchi: taglio donna, taglio uomo, piega
  UNION ALL SELECT '11111111-0000-0000-0000-000000000003', 'aaaa0001-0000-0000-0000-000000000001'
  UNION ALL SELECT '11111111-0000-0000-0000-000000000003', 'aaaa0001-0000-0000-0000-000000000002'
  UNION ALL SELECT '11111111-0000-0000-0000-000000000003', 'aaaa0001-0000-0000-0000-000000000005'
  -- Anna Rossi: taglio donna, colore, balayage, piega
  UNION ALL SELECT '22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000001'
  UNION ALL SELECT '22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000002'
  UNION ALL SELECT '22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000003'
  UNION ALL SELECT '22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000004'
  -- Luca Neri: colore, balayage
  UNION ALL SELECT '22222222-0000-0000-0000-000000000002', 'bbbb0001-0000-0000-0000-000000000002'
  UNION ALL SELECT '22222222-0000-0000-0000-000000000002', 'bbbb0001-0000-0000-0000-000000000003'
) AS s ON t.staff_id = s.staff_id AND t.service_id = s.service_id
WHEN NOT MATCHED THEN INSERT (staff_id, service_id) VALUES (s.staff_id, s.service_id);

-- ============================================================
-- Staff Schedules (all staff: Mon-Sat 10:00-18:00)
-- ============================================================

MERGE INTO mircom_test.virtual_assistant.staff_schedules AS t
USING (
  SELECT uuid() AS id, s.id AS staff_id, d.day AS day_of_week, '10:00' AS start_time, '18:00' AS end_time
  FROM mircom_test.virtual_assistant.staff s
  CROSS JOIN (SELECT 0 AS day UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5) d
) AS s ON t.staff_id = s.staff_id AND t.day_of_week = s.day_of_week
WHEN NOT MATCHED THEN INSERT (id, staff_id, day_of_week, start_time, end_time)
VALUES (s.id, s.staff_id, s.day_of_week, s.start_time, s.end_time);

-- ============================================================
-- Sample Customers
-- ============================================================

MERGE INTO mircom_test.virtual_assistant.customers AS t
USING (
  SELECT 'cccc0001-0000-0000-0000-000000000001' AS id, 'a0000000-0000-0000-0000-000000000001' AS shop_id, 'Maria Rossi' AS full_name, '11111111-0000-0000-0000-000000000001' AS preferred_staff_id
  UNION ALL SELECT 'cccc0001-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'Luca Ferrari', NULL
  UNION ALL SELECT 'cccc0002-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Francesca Bianchi', NULL
) AS s ON t.id = s.id
WHEN NOT MATCHED THEN INSERT (id, shop_id, full_name, preferred_staff_id)
VALUES (s.id, s.shop_id, s.full_name, s.preferred_staff_id);

-- ============================================================
-- Sample Phone Contacts
-- ============================================================

MERGE INTO mircom_test.virtual_assistant.phone_contacts AS t
USING (
  SELECT uuid() AS id, '+39 333 1111111' AS phone_number, 'cccc0001-0000-0000-0000-000000000001' AS customer_id
  UNION ALL SELECT uuid(), '+39 333 2222222', 'cccc0001-0000-0000-0000-000000000002'
  UNION ALL SELECT uuid(), '+39 333 3333333', 'cccc0002-0000-0000-0000-000000000001'
) AS s ON t.phone_number = s.phone_number AND t.customer_id = s.customer_id
WHEN NOT MATCHED THEN INSERT (id, phone_number, customer_id) VALUES (s.id, s.phone_number, s.customer_id);

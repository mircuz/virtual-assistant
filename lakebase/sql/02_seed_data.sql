-- Seed data: Two shops for testing
SET search_path TO hair_salon;

INSERT INTO shops (id, name, phone_number, address, welcome_message, tone_instructions, personality, special_instructions) VALUES
('a0000000-0000-0000-0000-000000000001'::uuid, 'Salon Bella', '+39 02 1234567', 'Via Roma 42, Milano',
 'Ciao, benvenuto da Salon Bella! Come ti chiami?',
 'Amichevole e informale, dai del tu al cliente',
 'Sei Bella, l''assistente virtuale del Salon Bella. Sei solare, cordiale e sempre pronta ad aiutare.',
 'Se il cliente chiede di un servizio che non offriamo, suggerisci il servizio più simile disponibile.');

INSERT INTO shops (id, name, phone_number, address, welcome_message, tone_instructions, personality, special_instructions) VALUES
('b0000000-0000-0000-0000-000000000002'::uuid, 'Studio Hair', '+39 06 7654321', 'Via del Corso 15, Roma',
 'Buongiorno, benvenuto allo Studio Hair. Come posso aiutarla?',
 'Professionale e formale, dia del lei al cliente',
 'Sei l''assistente dello Studio Hair. Sei professionale, preciso e attento ai dettagli.',
 NULL);

INSERT INTO staff (id, shop_id, full_name, role, bio) VALUES
('11111111-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Mirco Meazzo', 'stilista senior', 'Stilista con 15 anni di esperienza, specializzato in tagli moderni'),
('11111111-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Giulia Verdi', 'colorista', 'Esperta di colorazioni e trattamenti'),
('11111111-0000-0000-0000-000000000003'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Marco Bianchi', 'stilista', 'Specializzato in tagli classici e barba');

INSERT INTO staff (id, shop_id, full_name, role, bio) VALUES
('22222222-0000-0000-0000-000000000001'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Anna Rossi', 'stilista senior', 'Stilista di fama internazionale'),
('22222222-0000-0000-0000-000000000002'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Luca Neri', 'colorista', 'Esperto di balayage e meches');

INSERT INTO services (id, shop_id, service_name, description, duration_minutes, price_eur, category) VALUES
('aaaa0001-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Taglio donna', 'Taglio, shampoo e piega', 45, 35.00, 'taglio'),
('aaaa0001-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Taglio uomo', 'Taglio maschile classico o moderno', 30, 25.00, 'taglio'),
('aaaa0001-0000-0000-0000-000000000003'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Colore', 'Colorazione completa', 60, 55.00, 'colore'),
('aaaa0001-0000-0000-0000-000000000004'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Meches', 'Meches o colpi di sole', 90, 70.00, 'colore'),
('aaaa0001-0000-0000-0000-000000000005'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Piega', 'Piega semplice', 30, 20.00, 'piega'),
('aaaa0001-0000-0000-0000-000000000006'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Trattamento cheratina', 'Trattamento lisciante alla cheratina', 120, 90.00, 'trattamento');

INSERT INTO services (id, shop_id, service_name, description, duration_minutes, price_eur, category) VALUES
('bbbb0001-0000-0000-0000-000000000001'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Taglio donna', 'Taglio con consulenza personalizzata', 50, 45.00, 'taglio'),
('bbbb0001-0000-0000-0000-000000000002'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Colore', 'Colorazione premium', 75, 80.00, 'colore'),
('bbbb0001-0000-0000-0000-000000000003'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Balayage', 'Balayage naturale', 120, 120.00, 'colore'),
('bbbb0001-0000-0000-0000-000000000004'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Piega', 'Piega professionale', 30, 30.00, 'piega');

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
-- Anna (Shop B): taglio, colore, balayage, piega
INSERT INTO staff_services (staff_id, service_id) VALUES
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000001'::uuid),
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000002'::uuid),
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000003'::uuid),
('22222222-0000-0000-0000-000000000001'::uuid, 'bbbb0001-0000-0000-0000-000000000004'::uuid);
-- Luca (Shop B): colore, balayage
INSERT INTO staff_services (staff_id, service_id) VALUES
('22222222-0000-0000-0000-000000000002'::uuid, 'bbbb0001-0000-0000-0000-000000000002'::uuid),
('22222222-0000-0000-0000-000000000002'::uuid, 'bbbb0001-0000-0000-0000-000000000003'::uuid);

-- All staff 10:00-18:00 Mon-Sat (MVP)
-- day_of_week: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat
INSERT INTO staff_schedules (staff_id, day_of_week, start_time, end_time)
SELECT s.id, d.day, '10:00'::time, '18:00'::time
FROM staff s
CROSS JOIN (VALUES (0),(1),(2),(3),(4),(5)) AS d(day);

INSERT INTO customers (id, shop_id, full_name, preferred_staff_id) VALUES
('cccc0001-0000-0000-0000-000000000001'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Maria Rossi', '11111111-0000-0000-0000-000000000001'::uuid),
('cccc0001-0000-0000-0000-000000000002'::uuid, 'a0000000-0000-0000-0000-000000000001'::uuid, 'Luca Ferrari', NULL);

INSERT INTO phone_contacts (phone_number, customer_id) VALUES
('+39 333 1111111', 'cccc0001-0000-0000-0000-000000000001'::uuid),
('+39 333 2222222', 'cccc0001-0000-0000-0000-000000000002'::uuid);

INSERT INTO customers (id, shop_id, full_name) VALUES
('cccc0002-0000-0000-0000-000000000001'::uuid, 'b0000000-0000-0000-0000-000000000002'::uuid, 'Francesca Bianchi');

INSERT INTO phone_contacts (phone_number, customer_id) VALUES
('+39 333 3333333', 'cccc0002-0000-0000-0000-000000000001'::uuid);

INSERT INTO appointments (id, shop_id, customer_id, staff_id, start_time, end_time, status) VALUES
('dddd0001-0000-0000-0000-000000000001'::uuid,
 'a0000000-0000-0000-0000-000000000001'::uuid,
 'cccc0001-0000-0000-0000-000000000001'::uuid,
 '11111111-0000-0000-0000-000000000001'::uuid,
 '2026-03-30 10:00:00+01', '2026-03-30 10:45:00+01', 'scheduled');

INSERT INTO appointment_services (appointment_id, service_id, duration_minutes, price_eur) VALUES
('dddd0001-0000-0000-0000-000000000001'::uuid, 'aaaa0001-0000-0000-0000-000000000001'::uuid, 45, 35.00);

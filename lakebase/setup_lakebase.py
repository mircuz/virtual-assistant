# Databricks notebook source
# Setup Lakebase schema for Virtual Assistant

import psycopg

LB_HOST = "ep-rapid-heart-d1ftvh0y.database.us-west-2.cloud.databricks.com"
LB_PORT = 5432
LB_DB = "databricks_postgres"

# Get OAuth token from workspace context
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
auth = w.config.authenticate()
if isinstance(auth, dict):
    token = auth.get("Authorization", "").replace("Bearer ", "")
elif callable(auth):
    h = {}
    auth(h)
    token = h.get("Authorization", "").replace("Bearer ", "")

print(f"Token length: {len(token)}")

dsn = f"host={LB_HOST} port={LB_PORT} dbname={LB_DB} user=token password={token} sslmode=require"

with psycopg.connect(dsn) as conn:
    conn.autocommit = True
    print(f"Connected as: {conn.execute('SELECT current_user').fetchone()}")

    # Create database
    try:
        conn.execute("CREATE DATABASE virtual_assistant")
        print("Database created")
    except Exception as e:
        print(f"DB exists or error: {e}")

# Now connect to the virtual_assistant database
dsn2 = f"host={LB_HOST} port={LB_PORT} dbname=virtual_assistant user=token password={token} sslmode=require"

with psycopg.connect(dsn2) as conn:
    conn.autocommit = True

    # Create native login user
    pw = "VaBooking2026SecurePass!"
    try:
        conn.execute(f"CREATE ROLE booking_app LOGIN PASSWORD '{pw}'")
        print("User booking_app created")
    except Exception as e:
        print(f"User exists or error: {e}")

    # Grant privileges
    for sql in [
        "GRANT CONNECT ON DATABASE virtual_assistant TO booking_app",
        "GRANT ALL ON SCHEMA public TO booking_app",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO booking_app",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO booking_app",
    ]:
        try:
            conn.execute(sql)
        except Exception as e:
            print(f"Grant error: {e}")

    # Create schema
    SCHEMA_SQL = """
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

    CREATE TABLE IF NOT EXISTS staff_services (
        staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
        service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
        PRIMARY KEY (staff_id, service_id)
    );

    CREATE TABLE IF NOT EXISTS staff_schedules (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
        day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        CHECK (end_time > start_time),
        UNIQUE (staff_id, day_of_week)
    );

    CREATE TABLE IF NOT EXISTS customers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
        full_name TEXT NOT NULL,
        email TEXT,
        preferred_staff_id UUID REFERENCES staff(id) ON DELETE SET NULL,
        notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS phone_contacts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        phone_number TEXT NOT NULL,
        customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (phone_number, customer_id)
    );

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
        EXCLUDE USING gist (
            staff_id WITH =,
            tstzrange(start_time, end_time) WITH &&
        ) WHERE (status NOT IN ('cancelled', 'no_show'))
    );

    CREATE TABLE IF NOT EXISTS appointment_services (
        appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
        service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
        duration_minutes INTEGER NOT NULL,
        price_eur DECIMAL(8,2),
        PRIMARY KEY (appointment_id, service_id)
    );
    """

    for stmt in SCHEMA_SQL.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except Exception as e:
                print(f"Schema error: {e}")

    print("Schema created")

    # Seed data
    SEED_SQLS = [
        """INSERT INTO shops (id, name, phone_number, address, welcome_message, tone_instructions, personality, special_instructions) VALUES
        ('a0000000-0000-0000-0000-000000000001', 'Salon Bella', '+39 02 1234567', 'Via Roma 42, Milano',
         'Ciao, benvenuto da Salon Bella! Come ti chiami?',
         'Amichevole e informale, dai del tu al cliente',
         'Sei Bella, l''assistente virtuale del Salon Bella. Sei solare, cordiale e sempre pronta ad aiutare.',
         'Se il cliente chiede di un servizio che non offriamo, suggerisci il servizio più simile disponibile.')
        ON CONFLICT DO NOTHING""",

        """INSERT INTO shops (id, name, phone_number, address, welcome_message, tone_instructions, personality, special_instructions) VALUES
        ('b0000000-0000-0000-0000-000000000002', 'Studio Hair', '+39 06 7654321', 'Via del Corso 15, Roma',
         'Buongiorno, benvenuto allo Studio Hair. Come posso aiutarla?',
         'Professionale e formale, dia del lei al cliente',
         'Sei l''assistente dello Studio Hair. Sei professionale, preciso e attento ai dettagli.',
         NULL)
        ON CONFLICT DO NOTHING""",

        """INSERT INTO staff (id, shop_id, full_name, role, bio) VALUES
        ('11111111-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'Mirco Meazzo', 'stilista senior', 'Stilista con 15 anni di esperienza'),
        ('11111111-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'Giulia Verdi', 'colorista', 'Esperta di colorazioni e trattamenti'),
        ('11111111-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'Marco Bianchi', 'stilista', 'Specializzato in tagli classici e barba'),
        ('22222222-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Anna Rossi', 'stilista senior', 'Stilista di fama internazionale'),
        ('22222222-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'Luca Neri', 'colorista', 'Esperto di balayage e meches')
        ON CONFLICT DO NOTHING""",

        """INSERT INTO services (id, shop_id, service_name, description, duration_minutes, price_eur, category) VALUES
        ('aaaa0001-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'Taglio donna', 'Taglio, shampoo e piega', 45, 35.00, 'taglio'),
        ('aaaa0001-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'Taglio uomo', 'Taglio maschile classico o moderno', 30, 25.00, 'taglio'),
        ('aaaa0001-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'Colore', 'Colorazione completa', 60, 55.00, 'colore'),
        ('aaaa0001-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', 'Meches', 'Meches o colpi di sole', 90, 70.00, 'colore'),
        ('aaaa0001-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001', 'Piega', 'Piega semplice', 30, 20.00, 'piega'),
        ('aaaa0001-0000-0000-0000-000000000006', 'a0000000-0000-0000-0000-000000000001', 'Trattamento cheratina', 'Trattamento lisciante alla cheratina', 120, 90.00, 'trattamento'),
        ('bbbb0001-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Taglio donna', 'Taglio con consulenza personalizzata', 50, 45.00, 'taglio'),
        ('bbbb0001-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'Colore', 'Colorazione premium', 75, 80.00, 'colore'),
        ('bbbb0001-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000002', 'Balayage', 'Balayage naturale', 120, 120.00, 'colore'),
        ('bbbb0001-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000002', 'Piega', 'Piega professionale', 30, 30.00, 'piega')
        ON CONFLICT DO NOTHING""",

        """INSERT INTO staff_services (staff_id, service_id) VALUES
        ('11111111-0000-0000-0000-000000000001', 'aaaa0001-0000-0000-0000-000000000001'),
        ('11111111-0000-0000-0000-000000000001', 'aaaa0001-0000-0000-0000-000000000002'),
        ('11111111-0000-0000-0000-000000000001', 'aaaa0001-0000-0000-0000-000000000005'),
        ('11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000003'),
        ('11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000004'),
        ('11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000005'),
        ('11111111-0000-0000-0000-000000000002', 'aaaa0001-0000-0000-0000-000000000006'),
        ('11111111-0000-0000-0000-000000000003', 'aaaa0001-0000-0000-0000-000000000001'),
        ('11111111-0000-0000-0000-000000000003', 'aaaa0001-0000-0000-0000-000000000002'),
        ('11111111-0000-0000-0000-000000000003', 'aaaa0001-0000-0000-0000-000000000005'),
        ('22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000001'),
        ('22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000002'),
        ('22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000003'),
        ('22222222-0000-0000-0000-000000000001', 'bbbb0001-0000-0000-0000-000000000004'),
        ('22222222-0000-0000-0000-000000000002', 'bbbb0001-0000-0000-0000-000000000002'),
        ('22222222-0000-0000-0000-000000000002', 'bbbb0001-0000-0000-0000-000000000003')
        ON CONFLICT DO NOTHING""",

        """INSERT INTO staff_schedules (staff_id, day_of_week, start_time, end_time)
        SELECT s.id, d.day, '10:00'::time, '18:00'::time
        FROM staff s CROSS JOIN (VALUES (0),(1),(2),(3),(4),(5)) AS d(day)
        ON CONFLICT DO NOTHING""",

        """INSERT INTO customers (id, shop_id, full_name, preferred_staff_id) VALUES
        ('cccc0001-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'Maria Rossi', '11111111-0000-0000-0000-000000000001'),
        ('cccc0001-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'Luca Ferrari', NULL),
        ('cccc0002-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000002', 'Francesca Bianchi', NULL)
        ON CONFLICT DO NOTHING""",

        """INSERT INTO phone_contacts (phone_number, customer_id) VALUES
        ('+39 333 1111111', 'cccc0001-0000-0000-0000-000000000001'),
        ('+39 333 2222222', 'cccc0001-0000-0000-0000-000000000002'),
        ('+39 333 3333333', 'cccc0002-0000-0000-0000-000000000001')
        ON CONFLICT DO NOTHING""",
    ]

    for sql in SEED_SQLS:
        try:
            conn.execute(sql)
        except Exception as e:
            print(f"Seed error: {e}")

    print("Seed data inserted")

    # Create available_slots function
    FUNC_SQL = open('/Workspace/Users/mirco.meazzo@databricks.com/apps/va-setup/03_functions.sql').read()
    for stmt in FUNC_SQL.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("SET"):
            try:
                conn.execute(stmt)
            except Exception as e:
                print(f"Function error: {e}")

    # Verify
    for table in ['shops', 'staff', 'services', 'staff_services', 'staff_schedules', 'customers', 'phone_contacts']:
        count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")

    print("Setup complete!")
    print(f"Password for booking_app: {pw}")

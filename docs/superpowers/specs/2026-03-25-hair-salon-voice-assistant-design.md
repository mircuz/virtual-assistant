# Hair Salon Voice Booking Assistant — Design Spec

**Date:** 2026-03-25
**Status:** Draft
**Language:** Italian (MVP)

## Problem Statement

Build an AI-powered voice assistant that handles phone conversations for hair salon booking. The system manages multiple shops, each with their own stylists, services, schedules, and branded conversation experience. Customers can book, cancel, and reschedule appointments via natural Italian voice conversation.

## Scope — MVP

- Multi-shop support with per-shop branding/prompt configuration
- Book, cancel, reschedule appointments via voice
- Multi-service bookings with combined duration calculation
- Customer identification via name (caller ID stored silently for future marketing/reminders)
- Preferred stylist support with 3-working-day fallback suggestions
- Italian language only
- Guardrails: allow light chitchat, block off-topic
- All stylists/shops work 10AM–6PM
- Telephony-agnostic — architecture ready for future SIP/VoIP integration but MVP uses REST/WebSocket test interface
- Open-source models hosted on Databricks Model Serving

## Out of Scope (MVP)

- Telephony integration (Twilio, SIP, etc.)
- Admin UI for shop configuration
- Outbound reminders/notifications
- Voice cloning
- Multi-language support beyond Italian
- Payment processing

---

## Architecture: Two-Service Split

### Booking Engine (FastAPI REST)
Pure business logic — availability, booking, cancellation, rescheduling, customer lookup, shop config. Stateless, backed by Lakebase. No voice concerns.

### Voice Gateway (FastAPI + WebSocket)
Handles audio I/O, STT, TTS, session management, conversation state, LLM interaction. Calls the Booking Engine over HTTP for all business operations.

**Communication:** Voice Gateway → HTTP → Booking Engine → Lakebase

**Deployment:** Both deploy as independent Databricks Apps.

**Why this split:**
- Telephony-ready: future adapter pipes audio into Voice Gateway's WebSocket, Booking Engine unchanged
- Reusable: Booking Engine can serve web/mobile/WhatsApp in the future
- Testable: booking flow testable with plain HTTP, no audio required
- Independent scaling

---

## Data Model (Lakebase)

**Schema:** `hair_salon` (replaces the old `assistant_mochi` schema — clean-slate, no migration from previous schema)

**Timezone:** All `TIMESTAMPTZ` columns store UTC. All human-facing times are displayed in `Europe/Rome`. The `available_slots()` function operates in `Europe/Rome` for schedule matching.

**Day-of-week convention:** `0=Monday .. 6=Sunday` (ISO, matching `EXTRACT(ISODOW FROM ...) - 1`). Seed data must use this convention.

### shops
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | TEXT NOT NULL | |
| phone_number | TEXT | Shop contact number |
| address | TEXT | |
| welcome_message | TEXT | Branded greeting template |
| tone_instructions | TEXT | e.g., "friendly and informal" |
| personality | TEXT | Assistant personality description |
| special_instructions | TEXT | Additional prompt rules |
| is_active | BOOLEAN DEFAULT true | |

### staff
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| shop_id | UUID FK → shops.id | |
| full_name | TEXT NOT NULL | |
| role | TEXT | stilista, colorista, etc. |
| phone_number | TEXT | |
| email | TEXT | |
| bio | TEXT | |
| is_active | BOOLEAN DEFAULT true | |

### services
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| shop_id | UUID FK → shops.id | |
| service_name | TEXT NOT NULL | |
| description | TEXT | |
| duration_minutes | INTEGER NOT NULL | |
| price_eur | DECIMAL(8,2) | |
| category | TEXT | taglio, colore, trattamento, piega |
| is_active | BOOLEAN DEFAULT true | |

### staff_services (M2M)
| Column | Type | Notes |
|--------|------|-------|
| staff_id | UUID FK → staff.id | |
| service_id | UUID FK → services.id | |
| PK | (staff_id, service_id) | |

### staff_schedules
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| staff_id | UUID FK → staff.id | |
| day_of_week | INTEGER | 0=Mon..6=Sun |
| start_time | TIME | MVP: 10:00 for all |
| end_time | TIME | MVP: 18:00 for all |

### customers
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| shop_id | UUID FK → shops.id | Per-shop customer records |
| full_name | TEXT NOT NULL | |
| email | TEXT | |
| preferred_staff_id | UUID FK → staff.id | |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | |

### phone_contacts (soft link — caller ID)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| phone_number | TEXT NOT NULL | |
| customer_id | UUID FK → customers.id | |
| last_seen_at | TIMESTAMPTZ | |
| UNIQUE | (phone_number, customer_id) | Same phone can link to multiple people |

Not exposed in conversation. Used silently for matching and future marketing/reminders.

### appointments
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| shop_id | UUID FK → shops.id | Denormalized for direct per-shop queries and indexing |
| customer_id | UUID FK → customers.id | |
| staff_id | UUID FK → staff.id | |
| start_time | TIMESTAMPTZ NOT NULL | |
| end_time | TIMESTAMPTZ NOT NULL | Computed from sum of service durations |
| status | TEXT | scheduled, confirmed, completed, cancelled, no_show |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | |
| EXCLUDE | (staff_id, tstzrange) WHERE status NOT IN ('cancelled') | No double-booking |

### appointment_services (junction)
| Column | Type | Notes |
|--------|------|-------|
| appointment_id | UUID FK → appointments.id | |
| service_id | UUID FK → services.id | |
| duration_minutes | INTEGER | Snapshot at booking time |
| price_eur | DECIMAL(8,2) | Snapshot at booking time |
| PK | (appointment_id, service_id) | |

### available_slots() function
- Parameters: `p_shop_id UUID`, `p_from TIMESTAMPTZ`, `p_to TIMESTAMPTZ`, `p_service_ids UUID[]`, `p_staff_id UUID DEFAULT NULL`
- Internally computes `p_total_duration_minutes` by summing `duration_minutes` from `services` for all IDs in `p_service_ids`
- Filters staff to only those who appear in `staff_services` for **every** service ID in the array (capability check)
- Returns: available (staff_id, staff_name, start_time, end_time) combinations
- Logic: cross-join eligible staff schedules x time slots, subtract existing non-cancelled appointments, ensure contiguous block of `p_total_duration_minutes` fits within schedule window

**Dropped from old schema:** The `seats` table, `seat_id` on appointments, and `requires_seat_type` on services are intentionally removed. Seat/station management is not needed for the hair salon MVP and adds unnecessary complexity. Can be reintroduced in a future cycle if needed.

---

## Booking Engine API

**Base path:** `/api/v1`

### Shop Config
- `GET /shops/{shop_id}` — shop details + prompt config

### Customers
- `GET /shops/{shop_id}/customers?phone={number}` — caller ID lookup (returns list of matching customers for that phone)
- `GET /shops/{shop_id}/customers?name={name}&phone={number}` — match by name + phone
- `POST /shops/{shop_id}/customers` — create new customer `{full_name, phone_number?}`

### Services & Staff
- `GET /shops/{shop_id}/services` — list active services
- `GET /shops/{shop_id}/staff` — list active stylists
- `GET /shops/{shop_id}/staff/{staff_id}/services` — stylist's capabilities

### Availability
- `GET /shops/{shop_id}/availability?service_ids=X,Y&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&staff_id=Z`
- `service_ids` accepts multiple — durations are summed for contiguous slot search
- `staff_id` optional (customer preference)
- If preferred staff has no availability within date range, response includes `suggestions` field with alternative stylists and their available slots
- 3-working-day fallback logic lives here

### Appointments
- `POST /shops/{shop_id}/appointments` — book `{customer_id, service_ids[], staff_id, start_time}`
- `GET /shops/{shop_id}/appointments?customer_id=X&status=scheduled` — list upcoming
- `PATCH /shops/{shop_id}/appointments/{id}/cancel` — cancel
- `PATCH /shops/{shop_id}/appointments/{id}/reschedule` — `{new_start_time, new_staff_id?}` — atomic cancel + rebook in transaction. Service modification during reschedule is out of scope for MVP (cancel + new booking for that).

### Error Response Schema

All Booking Engine errors return:
```json
{"error": "<error_code>", "message": "<human-readable detail>"}
```

Key error codes:
| Code | HTTP Status | When |
|------|-------------|------|
| `shop_not_found` | 404 | Invalid shop_id |
| `customer_not_found` | 404 | Invalid customer_id |
| `appointment_not_found` | 404 | Invalid appointment_id |
| `slot_taken` | 409 | Race condition — slot booked between check and book |
| `staff_unavailable` | 409 | Staff schedule conflict |
| `no_slots_available` | 200 | No availability (not an error, empty result) |
| `invalid_service` | 400 | Service ID doesn't exist or is inactive |
| `appointment_not_cancellable` | 409 | Already cancelled/completed |

The Voice Gateway maps these to natural spoken responses via the Response Composer.

---

## Voice Gateway

### Endpoints
- `POST /conversations/start` — `{shop_id, caller_phone?}` → `{session_id, greeting_audio, greeting_text}`
- `POST /conversations/{session_id}/turn` — `{audio_base64? | text?}` → `{response_text, response_audio, action_taken?}`
- `DELETE /conversations/{session_id}` — end conversation
- `WS /conversations/{session_id}/stream` — bidirectional audio streaming (scaffolded for future telephony)

### Session Lifecycle

**Start:**
1. Load shop config from Booking Engine
2. Assemble system prompt deterministically from shop config
3. If `caller_phone` provided, silently store/update in `phone_contacts` via Booking Engine
4. Generate branded greeting via TTS
5. Always ask for customer's name (never reveal caller ID knowledge)

**Turn Processing Pipeline:**
1. Audio → STT (Whisper on Databricks) → text
2. Text → Intent Router (small LLM, temperature=0) → `{action, args, confidence, topic}`
3. If `topic == off_topic` → polite decline, no Booking Engine call
4. If `topic == chitchat` → brief friendly response + gentle redirect
5. If required args missing → clarification request
6. If action clear → call Booking Engine REST API (with filler audio: "Un momento...")
7. Result → Response Composer (large LLM, temperature=0.7) → natural Italian 1-2 sentences
8. Text → TTS (Kokoro on Databricks) → audio
9. Return response

**End:**
- Generate farewell, cleanup in-memory session state

### Session State (in-memory, ephemeral)
- `session_id`, `shop_id`, `shop_config`, `customer` (once identified)
- `system_prompt`, `conversation_history[]`, `current_phase`
- **History limit:** sliding window of last 20 turns. Older turns are dropped. This prevents LLM context overflow and memory growth for unusually long calls.
- No persistence — appointment data lives in Lakebase via Booking Engine

### Customer Identification Flow
1. Assistant always asks "Come ti chiami?"
2. Customer says name
3. If `caller_phone` was provided: query Booking Engine for customers linked to that phone in this shop
4. **Name matching strategy:** case-insensitive first-name prefix match (e.g., "Maria" matches "Maria Rossi"). If multiple matches, ask for confirmation: "Sei Maria Rossi o Maria Bianchi?"
5. If single match found → link to existing customer, load preferences silently
6. If no match → create new customer, link phone silently
7. If no `caller_phone` → create/match by name + shop only
8. **Ambiguity guard:** if a phone has 5+ linked customers and none match, skip phone linking to avoid unbounded growth from STT transcription variance

---

## LLM Integration

### Two-Model Strategy

**Intent Router — Small/Fast Model (e.g., Llama 3.1 8B on Databricks Model Serving)**
- Temperature: 0
- Output: strict JSON `{"action": "...", "args": {...}, "confidence": 0.0-1.0, "topic": "booking_related|chitchat|off_topic"}`
- Actions: `check_availability`, `book`, `cancel`, `reschedule`, `list_appointments`, `ask_service_info`, `chitchat`, `off_topic`, `provide_name`, `none`
- Guardrail is embedded — `topic` field classifies topicality in the same call
- Prompt includes shop's service names and staff names for entity extraction

**Response Composer — Large Model (e.g., Llama 3.3 70B on Databricks Model Serving)**
- Temperature: 0.7
- Receives: system prompt (with shop personality), conversation history, action result
- Generates natural Italian, max 1-2 sentences (voice-optimized)

### Prompt Templates (deterministic, not LLM-generated)

**Intent router prompt:**
```
Sei un classificatore di intenti per un salone di parrucchieri.
Servizi disponibili: {shop_services}
Staff disponibile: {shop_staff}
Data e ora corrente: {now}

Classifica il messaggio del cliente e estrai i parametri.
Azioni possibili: check_availability, book, cancel, reschedule,
list_appointments, ask_service_info, provide_name, chitchat, off_topic

Rispondi SOLO in JSON...
```

**System prompt for response composer:**
```
{shop_personality}
{tone_instructions}

Sei l'assistente vocale di {shop_name}. Aiuti i clienti a prenotare
appuntamenti, verificare disponibilità, e gestire le loro prenotazioni.

Regole:
- Rispondi sempre in italiano
- Massimo 1-2 frasi per risposta (conversazione vocale)
- Sii {tone} e professionale
- Se il cliente chiede qualcosa fuori tema, rispondi brevemente
  e riporta la conversazione sulle prenotazioni
- Non inventare informazioni su disponibilità o prezzi

{special_instructions}
```

### Filler Responses
Pre-defined per shop tone. Examples: "Un momento, controllo subito...", "Dammi un attimo..."

**Delivery mechanism:** In the REST turn endpoint, fillers are not applicable (single request/response). Fillers are used only in the WebSocket streaming path — sent as an immediate audio frame before the full response. The REST endpoint returns the complete response after processing.

### Intent Router Robustness
The small model (8B) may occasionally produce malformed JSON. Mitigation strategy:
1. Attempt JSON parse
2. If malformed, attempt JSON repair (strip markdown fences, fix trailing commas)
3. If still invalid, retry once with a stricter re-prompt
4. If still failing, fall back to `{action: "none", topic: "booking_related"}` and let the response composer ask for clarification

### `none` Action Handling
When the intent router returns `action: "none"` with `topic: "booking_related"`, the response composer generates a generic prompt: "Non ho capito bene, puoi ripetere?" or "Come posso aiutarti con la prenotazione?"

---

## Guardrails

Implemented via the intent router's `topic` classification:

- **`booking_related`** — proceed normally
- **`chitchat`** — greetings, "come stai?", weather, small talk → brief friendly response + redirect to booking. Handled by response composer without Booking Engine call.
- **`off_topic`** — politics, medical advice, finance, jailbreak attempts → polite decline: "Mi occupo solo di prenotazioni e servizi per capelli!"

System prompt reinforces boundaries. No separate guardrail model needed — the intent router handles it in one call.

---

## Conversation Flows

### Flow 1: Book with preferred stylist (multi-service)
```
Assistant: "Ciao, benvenuto da Shop A! Come ti chiami?"
Caller: "Maria"
→ Silent: phone+name match → existing customer, load preferences
Assistant: "Ciao Maria! Come posso aiutarti?"
Maria: "Vorrei taglio e colore con Mirco domani"
→ Intent: {action: check_availability, args: {services: ["taglio", "colore"], staff: "Mirco", date: tomorrow}}
→ Booking Engine: duration = 30+60 = 90min, find 90min slots for Mirco tomorrow
→ Result: [10:00-11:30, 14:00-15:30]
Assistant: "Mirco è disponibile domani dalle 10 alle 11:30 o dalle 14 alle 15:30. Quando preferisci?"
Maria: "Alle 14"
→ Booking Engine: POST /appointments {services: [taglio, colore], staff: Mirco, start: 14:00}
Assistant: "Perfetto, taglio e colore con Mirco domani dalle 14 alle 15:30. Ti aspettiamo!"
```

### Flow 2: Preferred stylist unavailable — suggestions
```
Maria: "Voglio un colore con Mirco questa settimana"
→ Booking Engine: no Mirco slots for colore in next 3 working days
→ Suggestions: [{staff: "Laura", slots: [tomorrow 10:00, ...]}, ...]
Assistant: "Mi dispiace, Mirco non ha disponibilità nei prossimi giorni per il colore. Laura è disponibile domani alle 10 o mercoledì alle 15. Vuoi prenotare con Laura o preferisci un'altra data con Mirco?"
```

### Flow 3: New caller registration
```
Phone not in DB, or name doesn't match existing records
Assistant: "Ciao, benvenuto da Shop A! Come ti chiami?"
Caller: "Marco Rossi"
→ No match → create new customer + link phone silently
Assistant: "Piacere Marco! Come posso aiutarti oggi?"
```

### Flow 4: Cancel
```
Maria: "Devo cancellare l'appuntamento di domani"
→ Booking Engine: GET /appointments?customer_id=X&status=scheduled
→ [{service: "taglio", staff: "Mirco", time: "14:00"}]
Assistant: "Hai il taglio con Mirco domani alle 14. Vuoi cancellarlo?"
Maria: "Sì"
→ Booking Engine: PATCH /appointments/ABC/cancel
Assistant: "Fatto, l'appuntamento è stato cancellato. Posso aiutarti con altro?"
```

### Flow 5: Reschedule
```
Maria: "Posso spostare l'appuntamento di domani a giovedì?"
→ Booking Engine: find current appointment + check Thursday availability
→ Thursday slots: [10:00, 11:00, 15:00]
Assistant: "Giovedì Mirco è disponibile alle 10, 11 o alle 15. Quale orario?"
Maria: "Alle 11"
→ Booking Engine: PATCH /appointments/ABC/reschedule {new_start_time: thursday 11:00}
Assistant: "Spostato! Taglio con Mirco giovedì alle 11. Ci vediamo!"
```

### Flow 6: Off-topic (blocked)
```
Caller: "Cosa ne pensi delle elezioni?"
→ Intent: {topic: off_topic}
Assistant: "Non saprei dirti, mi occupo solo di prenotazioni e servizi per capelli! Posso aiutarti con un appuntamento?"
```

### Flow 7: Chitchat (allowed, redirected)
```
Caller: "Ciao, come stai?"
→ Intent: {topic: chitchat}
Assistant: "Bene grazie! Dimmi, come posso aiutarti oggi?"
```

---

## Project Structure

```
virtual-assistant/
├── booking_engine/
│   ├── api/
│   │   ├── app.py                  # FastAPI app
│   │   ├── models.py              # Pydantic request/response
│   │   └── routes/
│   │       ├── shops.py           # GET /shops/{id}
│   │       ├── customers.py       # Lookup + create
│   │       ├── services.py        # List services, staff
│   │       ├── availability.py    # Slot query + suggestions
│   │       └── appointments.py    # Book, cancel, reschedule
│   ├── db/
│   │   ├── connection.py          # Lakebase connection pool
│   │   └── queries.py            # SQL query functions
│   ├── config.py                  # Settings from env
│   └── __init__.py
├── voice_gateway/
│   ├── api/
│   │   ├── app.py                 # FastAPI app
│   │   ├── models.py             # Pydantic models
│   │   └── routes/
│   │       ├── conversations.py   # Start, turn, end
│   │       └── ws.py             # WebSocket streaming (scaffold)
│   ├── conversation/
│   │   ├── session.py            # Session state management
│   │   ├── prompt_assembler.py   # Per-shop prompt building
│   │   ├── intent_router.py      # Small LLM intent + guardrails
│   │   └── response_composer.py  # Large LLM natural responses
│   ├── voice/
│   │   ├── stt.py                # Whisper endpoint client
│   │   └── tts.py                # Kokoro endpoint client
│   ├── clients/
│   │   └── booking_client.py     # HTTP client to Booking Engine
│   ├── config.py                 # Settings from env
│   └── __init__.py
├── lakebase/
│   ├── sql/
│   │   ├── 01_schema.sql         # Full schema with shops
│   │   ├── 02_seed_data.sql      # Sample shop + staff + services
│   │   └── 03_functions.sql      # available_slots() revised
│   └── config/
│       └── lakebase.env
├── tests/
│   ├── booking_engine/           # Integration tests (real Lakebase)
│   └── voice_gateway/            # Unit tests (mocked Booking Engine)
├── requirements.txt
└── README.md
```

### Files to Delete
- `realtime_voice/` — legacy duplicate module
- `personaplex_based/` — empty legacy directory
- `.cursor/` — Cursor AI agent profiles
- `virtual_assistant/` — entire old module (replaced by booking_engine + voice_gateway)

---

## Deployment

Both services deploy as **Databricks Apps**, each with its own `app.yaml`.

### Booking Engine
- Connects to Lakebase directly
- Env vars: `LAKEBASE_HOST`, `LAKEBASE_PORT`, `LAKEBASE_DB`, `LAKEBASE_USER`, `LAKEBASE_PASSWORD`, `LAKEBASE_SCHEMA`

### Voice Gateway
- Connects to Databricks Model Serving endpoints + Booking Engine
- Env vars: `BOOKING_ENGINE_URL`, `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `STT_ENDPOINT`, `TTS_ENDPOINT`, `INTENT_LLM_ENDPOINT`, `RESPONSE_LLM_ENDPOINT`

---

## MVP Test Interface

- **Text-mode API**: `POST /conversations/{session_id}/turn` with `text` field — full pipeline minus STT/TTS, for development and debugging
- **Gradio UI**: Minimal web page with microphone — record, send to Voice Gateway, play response audio. Standalone script, not embedded in either service.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Booking Engine | FastAPI, Pydantic, psycopg (v3, async-native) |
| Voice Gateway | FastAPI, WebSocket, httpx |
| Database | Databricks Lakebase (PostgreSQL) |
| STT | Whisper (Databricks Model Serving) |
| TTS | Kokoro (Databricks Model Serving) |
| Intent Router | Llama 3.1 8B (Databricks Model Serving) |
| Response Composer | Llama 3.3 70B (Databricks Model Serving) |
| Test UI | Gradio |
| Deployment | Databricks Apps |

---

## Deferred Decisions (documented for future cycles)

- **Rate limiting / abuse protection** — not needed for MVP (no public exposure), add when telephony is integrated
- **Service modification during reschedule** — MVP requires cancel + new booking; first-class service change can be added later
- **Seat/station management** — intentionally dropped from old schema; reintroduce if shops need to track physical stations
- **Voice cloning** — architecture supports swapping TTS endpoint; OpenVoice or XTTS can replace Kokoro when ready
- **Outbound reminders** — `phone_contacts` table already stores the data needed; add a notification service in a future cycle

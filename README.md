# Virtual Assistant — Voice Booking System

AI-powered real-time voice assistant for appointment booking, built on Databricks and OpenAI Realtime API.

## Architecture

```
Customer (browser/WebRTC) ←→ OpenAI Realtime API (voice + LLM)
                                    ↕ function calls
                              Voice Gateway (proxy)
                                    ↕ HTTP
                              Booking Engine (REST)
                                    ↕ SQL
                              Delta Tables (mircom_test.virtual_assistant)
```

**Booking Engine** — Stateless REST API for shops, staff, services, customers, availability, and appointments. Backed by Delta tables on Databricks SQL warehouse.

**Voice Gateway** — Generates ephemeral OpenAI Realtime API tokens with session config (tools, voice, VAD) and proxies function calls from the browser to the Booking Engine.

**OpenAI Realtime API** — Handles STT, LLM reasoning, TTS, and voice activity detection natively via WebRTC. The browser connects directly to OpenAI for audio streaming.

## Project Structure

```
booking_engine/          # REST API (FastAPI + Delta tables)
├── api/routes/          # Shops, customers, services, availability, appointments
├── db/                  # Databricks SQL connector + queries
├── config.py            # Settings from env vars
└── app.yaml             # Databricks App config

voice_gateway/           # Realtime API gateway (FastAPI)
├── api/routes/
│   └── realtime.py      # Token generation + function call proxy
├── clients/
│   └── booking_client.py # Booking Engine HTTP client
├── static/
│   └── index.html       # WebRTC phone-call UI
├── config.py            # Settings from env vars
└── app.yaml             # Databricks App config

docs/superpowers/        # Design spec + implementation plan
```

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
export BOOKING_ENGINE_URL=https://your-booking-engine.databricksapps.com
export OPENAI_KEY=sk-proj-...
```

Or create a `.env` file with these values.

### 3. Run locally

```bash
# Booking Engine (requires Databricks SQL warehouse access)
uvicorn booking_engine.api.app:create_app --factory --port 8000

# Voice Gateway
uvicorn voice_gateway.api.app:create_app --factory --port 8001
```

Open http://localhost:8001 to access the phone-call UI.

### 4. Test function calls

```bash
# Check availability
curl -s -X POST http://localhost:8001/api/v1/realtime/action \
  -H "Content-Type: application/json" \
  -d '{"shop_id": "a0000000-0000-0000-0000-000000000001", "function_name": "check_availability", "arguments": {"services": ["Taglio donna"], "date": "2026-03-28"}}' | jq .
```

## Deployment

Both services deploy as Databricks Apps on `e2-demo-field-eng`. See `booking_engine/app.yaml` and `voice_gateway/app.yaml`.

- **Booking Engine**: `https://virtual-assistant-booking-1444828305810485.aws.databricksapps.com`
- **Voice Gateway**: `https://virtual-assistant-gateway-1444828305810485.aws.databricksapps.com`
- **Database**: `mircom_test.virtual_assistant` (9 Delta tables) via SQL warehouse `03560442e95cb440`

## Design Docs

- [Design Spec](docs/superpowers/specs/2026-03-25-hair-salon-voice-assistant-design.md)
- [Implementation Plan](docs/superpowers/plans/2026-03-25-hair-salon-voice-assistant.md)

> Note: Design docs describe the original Lakebase/two-LLM architecture. The current implementation uses Delta tables and OpenAI Realtime API instead.

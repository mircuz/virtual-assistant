# Hair Salon Voice Booking Assistant

AI-powered voice assistant for hair salon appointment booking, built on Databricks.

## Architecture

Two independent services communicating over HTTP:

```
Customer (phone/web) → Voice Gateway → Booking Engine → Lakebase (PostgreSQL)
                        ↕
                   Databricks Model Serving
                   (Whisper STT, Kokoro TTS,
                    Llama 8B, Llama 70B)
```

**Booking Engine** — Stateless REST API for shops, staff, services, customers, availability, and appointments.

**Voice Gateway** — Conversation orchestrator handling STT/TTS, intent routing (small LLM), response generation (large LLM), and per-shop branded prompts.

## Project Structure

```
booking_engine/          # REST API (FastAPI)
├── api/routes/          # Shops, customers, services, availability, appointments
├── db/                  # Async psycopg connection pool + SQL queries
├── config.py            # Settings from env vars
└── app.yaml             # Databricks App config

voice_gateway/           # Conversation service (FastAPI + WebSocket)
├── api/routes/          # Start, turn, end conversation + WS scaffold
├── conversation/        # Session, prompt assembler, intent router, response composer
├── voice/               # STT + TTS endpoint clients
├── clients/             # Booking Engine HTTP client
├── llm.py               # Databricks Model Serving predict functions
└── app.yaml             # Databricks App config

lakebase/sql/            # Database schema, seed data, functions
tests/                   # 31 tests (pytest)
docs/superpowers/        # Design spec + implementation plan
```

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Deploy Lakebase schema

Run in order on your Databricks Lakebase instance:
```
lakebase/sql/01_schema.sql
lakebase/sql/02_seed_data.sql
lakebase/sql/03_functions.sql
```

### 3. Run Booking Engine

```bash
export LAKEBASE_HOST=your-lakebase-host
export LAKEBASE_USER=your-user
export LAKEBASE_PASSWORD=your-password

uvicorn booking_engine.api.app:create_app --factory --port 8000
```

### 4. Run Voice Gateway

```bash
export BOOKING_ENGINE_URL=http://localhost:8000
export DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
export DATABRICKS_TOKEN=your-token

uvicorn voice_gateway.api.app:create_app --factory --port 8001
```

### 5. Test a conversation (text mode)

```bash
# Start
curl -s -X POST http://localhost:8001/conversations/start \
  -H "Content-Type: application/json" \
  -d '{"shop_id": "a0000000-0000-0000-0000-000000000001"}' | jq .

# Send a turn
curl -s -X POST http://localhost:8001/conversations/{session_id}/turn \
  -H "Content-Type: application/json" \
  -d '{"text": "Sono Maria, vorrei un taglio con Mirco domani"}' | jq .
```

## Running Tests

```bash
pytest tests/ -v
```

## Deployment

Both services deploy as Databricks Apps. See `booking_engine/app.yaml` and `voice_gateway/app.yaml`.

## Design Docs

- [Design Spec](docs/superpowers/specs/2026-03-25-hair-salon-voice-assistant-design.md)
- [Implementation Plan](docs/superpowers/plans/2026-03-25-hair-salon-voice-assistant.md)

# Virtual Assistant

A business-configurable voice assistant backed by Databricks Model Serving and Lakebase.

## New Flow

```
1. Specify your business  →  AI generates a tailored system prompt  →  Conversation starts
```

Instead of a hardcoded Italian hair-salon bot, you configure any business type and the assistant adapts automatically.

---

## Architecture

```
virtual_assistant/
├── core/
│   ├── business_config.py   # BusinessConfig dataclass + enums
│   ├── prompt_builder.py    # LLM-based system prompt generation
│   ├── session.py           # Session state + SessionManager
│   ├── engine.py            # Core Engine (sync) + ConversationEngine ABC
│   └── engine_impl.py       # DatabricksConversationEngine (production)
├── agents/
│   ├── base.py              # BaseAgent ABC
│   ├── registry.py          # AgentRegistry (pluggable tools)
│   ├── database.py          # Lakebase / PostgreSQL helpers
│   └── tools/
│       ├── availability.py  # Check appointment availability
│       └── booking.py       # Book an appointment
├── api/
│   ├── app.py               # FastAPI application
│   ├── models.py            # Pydantic request/response models
│   └── routes/
│       ├── health.py        # GET /health
│       └── sessions.py      # Session CRUD + turn processing
├── voice/
│   ├── stt.py               # Speech-to-text (faster-whisper + VAD)
│   └── tts.py               # Text-to-speech (Databricks Kokoro endpoint)
├── integrations/
│   └── databricks.py        # Databricks predict_fn factory
└── config/
    └── settings.py          # Settings loaded from env vars
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `lakebase/config/lakebase.env` and fill in your values:

```env
DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
DATABRICKS_TOKEN=your-token
DATABRICKS_ENDPOINT=personaplex-7b-endpoint
LAKEBASE_HOST=your-lakebase-host
LAKEBASE_USER=your-user
LAKEBASE_PASSWORD=your-password
```

### 3. Run the API

```bash
uvicorn virtual_assistant.api.app:app --reload --port 8000
```

### 4. Create a session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "business": {
      "name": "Salon Bella",
      "business_type": "hair_salon",
      "services": ["taglio", "colore", "piega"],
      "language": "it",
      "tone": "friendly"
    }
  }'
```

Response:
```json
{
  "session_id": "abc-123",
  "generated_system_prompt": "Sei l'assistente virtuale di Salon Bella...",
  "greeting": "Ciao! Benvenuto da Salon Bella. Come posso aiutarti oggi?",
  "business_name": "Salon Bella",
  "language": "it"
}
```

### 5. Send a turn

```bash
curl -X POST http://localhost:8000/sessions/abc-123/turns \
  -H "Content-Type: application/json" \
  -d '{"text": "Vorrei prenotare un taglio per domani"}'
```

### 6. End the session

```bash
curl -X DELETE http://localhost:8000/sessions/abc-123
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/sessions` | Create session (generates system prompt) |
| `POST` | `/sessions/{id}/turns` | Process a conversation turn |
| `GET` | `/sessions/{id}` | Get session summary |
| `DELETE` | `/sessions/{id}` | End session |

Full interactive docs at `http://localhost:8000/docs`.

---

## Business Types

| Key | Description |
|-----|-------------|
| `hair_salon` | Hair salon — haircuts, coloring, treatments |
| `restaurant` | Restaurant — reservations, menus |
| `dental_clinic` | Dental clinic — appointments, consultations |
| `medical_clinic` | Medical clinic — appointments, specialties |
| `spa` | Spa — treatments, massages |
| `gym` | Gym — class bookings, personal training |
| `general` | Any business |

---

## Adding Custom Agents

Implement `BaseAgent` and register it:

```python
from virtual_assistant.agents.base import BaseAgent

class MyTool(BaseAgent):
    @property
    def name(self) -> str:
        return "my_action"

    def execute(self, args: dict) -> Any:
        # your logic here
        return {"result": "..."}

registry.register("my_action", MyTool())
```

Then include `"my_action"` in the `agent_capabilities` list when creating a session.

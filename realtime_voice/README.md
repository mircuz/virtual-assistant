# Real-Time Voice Assistant (MVP)

Simple, data-grounded voice assistant for appointment workflows.

## Features

- **Grounded Responses**: answers are based on tool outputs from Lakebase
- **Two Core Actions**: availability check and booking
- **Voice Optional**: STT + TTS endpoint integration
- **Italian-only**: prompts and STT configured for Italian
- **Modular Components**: routing, agents, STT, TTS can run independently
- **Booking Notes**: optional `notes` saved on the appointment record

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     RealtimeAssistant                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Streaming   │  │   Intent     │  │   Agent      │          │
│  │    STT       │──│   Router     │──│  Dispatcher  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                │                  │                   │
│         ▼                ▼                  ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Conversation │  │   Filler     │  │  Response    │          │
│  │   Manager    │──│  Generator   │──│  Composer    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                           │                                     │
│                           ▼                                     │
│                    ┌──────────────┐                            │
│                    │ TTS Manager  │                            │
│                    │ (Endpoint)   │                            │
│                    └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# If you use endpoint TTS, set env vars for Databricks serving
# DATABRICKS_TTS_ENDPOINT and TTS_VOICE
```

## Configuration

Set these environment variables (or use a `.env` file):

```bash
# Language (fixed)
ASSISTANT_LANGUAGE=it

# Databricks
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-token
DATABRICKS_ENDPOINT=personaplex-7b-endpoint

# Database (Lakebase)
LAKEBASE_HOST=your-db-host
LAKEBASE_PORT=5432
LAKEBASE_DB=databricks_postgres
LAKEBASE_USER=your-user
LAKEBASE_PASSWORD=your-password
LAKEBASE_SCHEMA=assistant_mochi

# Voice (optional)
ENABLE_VOICE=true
DATABRICKS_TTS_ENDPOINT=kokoro-tts-endpoint
TTS_VOICE=af_sky
VOLUME_BASE=/Volumes/your/volume/path
```

## Quick Start

### Python Script

```python
from realtime_voice.realtime_assistant import RealtimeAssistant

# Create a prediction function for your LLM
def predict(prompt: str, max_tokens: int) -> str:
    # Your LLM call here
    pass

# Initialize
assistant = RealtimeAssistant(
    predict_fn=predict,
    language="it",
    enable_tts=True,
)

# Start conversation
assistant.start_conversation(customer_context={"customer_id": "CUST001"})

# Process turns
result = assistant.process_text_turn("Vorrei prenotare un taglio per domani")
print(result.response_text)

# End conversation
assistant.end_conversation()
```

### Databricks Notebook

```python
# Import integration module
from realtime_voice.notebook_integration import (
    setup_assistant,
    process_text_input,
)

# Setup with Databricks environment
assistant = setup_assistant(
    env_file="/Volumes/your/path/lakebase.env",
    language="it",
)

# Process input
result = process_text_input(
    assistant,
    "Ciao, vorrei prenotare un taglio",
    customer_id="CUST001",
)
```

## Module Structure

```
realtime_voice/
├── __init__.py
├── realtime_assistant.py      # Main orchestrator
├── intent_router.py           # Intent extraction & routing
├── notebook_integration.py    # Databricks integration
├── requirements.txt
├── README.md
│
├── conversation/
│   ├── __init__.py
│   ├── language_config.py     # Italian-only configuration
│   ├── state_manager.py       # Conversation state machine
│   ├── filler_generator.py    # Natural filler responses
│   └── response_composer.py   # Agent result → natural response
│
├── agents/
│   ├── __init__.py
│   ├── dispatcher.py          # Async agent execution
│   ├── database.py            # PostgreSQL utilities
│   ├── availability_agent.py  # Check appointment availability
│   └── booking_agent.py       # Book appointments
│
├── voice/
│   ├── __init__.py
│   ├── streaming_stt.py       # VAD + Whisper transcription
│   └── tts_manager.py         # Endpoint TTS wrapper
│
└── notebooks/
    └── realtime_voice_notebook.py  # Databricks notebook
```

## Conversation Flow

```
Customer: "Ciao, vorrei prenotare un taglio per domani"
    │
    ▼
┌─────────────────┐
│ STT Transcribe  │  (faster-whisper, lang=it)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Intent Router   │  → {action: check_availability, args: {...}}
└────────┬────────┘
         │
         ├──────────────────────┐
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ Filler: "Un     │    │ Agent Dispatch  │  (async)
│ attimo..."      │    │ check_availability
└────────┬────────┘    └────────┬────────┘
         │                      │
         ▼                      ▼
    [TTS speaks]         [Query database]
                               │
                               ▼
                    ┌─────────────────┐
                    │ Agent Result:   │
                    │ [3 slots found] │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Response        │
                    │ Composer        │
                    └────────┬────────┘
                             │
                             ▼
    "Abbiamo disponibilità alle 10, alle 14, o alle 16:30.
     Quale preferisce?"
```

## Language Configuration

This MVP is Italian-only:
- Greetings: "Buongiorno! Come posso aiutarla?"
- Fillers: "Un attimo...", "Fammi verificare...", "Vediamo un po'..."
- Error: "Mi scusi, non ho capito. Può ripetere per favore?"

## Extending with New Agents

1. Create a new agent in `agents/`:

```python
# agents/new_agent.py
from .database import fetch_all, get_schema

def my_new_action(param1: str, param2: str) -> dict:
    """Your agent logic."""
    # Query database, call APIs, etc.
    return {"result": "..."}
```

2. Register in `realtime_assistant.py`:

```python
self._agent_functions = {
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "my_new_action": my_new_action,  # Add here
}
```

3. Update router prompts in `intent_router.py` to include the new action.

## Testing

```python
# Test without TTS
assistant = RealtimeAssistant(
    predict_fn=predict,
    language="it",
    enable_tts=False,
)

# Or use mock TTS
assistant = RealtimeAssistant(
    predict_fn=predict,
    language="it",
    enable_tts=True,
    mock_tts=True,  # Won't actually generate audio
)
```

## License

Internal use only.

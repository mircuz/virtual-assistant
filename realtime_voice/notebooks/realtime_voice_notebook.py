# Databricks notebook source
# MAGIC %md
# MAGIC # Real-Time Voice Assistant (Italian-only)
# MAGIC 
# MAGIC Natural, human-like voice conversations for appointment booking.
# MAGIC 
# MAGIC **Features:**
# MAGIC - Parallel processing with natural fillers
# MAGIC - Italian-only prompts and STT
# MAGIC - Async agent execution
# MAGIC - Human-like conversation flow

# COMMAND ----------
# MAGIC %pip install requests psycopg2-binary faster-whisper torch numpy

# COMMAND ----------
# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------
import os
import sys

# Widgets for configuration
dbutils.widgets.text("ENV_FILE", "", "Environment file path")
dbutils.widgets.text("VOLUME_BASE", "", "Volume base path")
dbutils.widgets.text("LANGUAGE", "it", "Assistant language (fixed)")
dbutils.widgets.dropdown("ENABLE_TTS", "true", ["true", "false"], "Enable TTS")

env_file = dbutils.widgets.get("ENV_FILE").strip()
volume_base = dbutils.widgets.get("VOLUME_BASE").strip()
language = "it"
enable_tts = dbutils.widgets.get("ENABLE_TTS").strip().lower() == "true"

# Set language environment variable
os.environ["ASSISTANT_LANGUAGE"] = language

# Infer paths
if not env_file and volume_base:
    env_file = f"{volume_base.rstrip('/')}/lakebase.env"
if env_file:
    os.environ["ENV_FILE"] = env_file
if volume_base:
    os.environ["VOLUME_BASE"] = volume_base

print(f"Language: {language}")
print(f"TTS Enabled: {enable_tts}")
print(f"Env file: {env_file}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Load Environment

# COMMAND ----------
from pathlib import Path

def load_env(env_path: str) -> None:
    """Load environment variables from file."""
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")

if env_file:
    load_env(env_file)
    print("Environment loaded successfully")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Initialize Assistant

# COMMAND ----------
# Add realtime_voice to path
# Adjust based on your repo structure
repo_path = "/Workspace/Repos/mirco.meazzo@databricks.com/virtual-assistant"
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

# Import components
from realtime_voice.notebook_integration import (
    create_databricks_predict_fn,
)
from realtime_voice.realtime_assistant import RealtimeAssistant
from realtime_voice.conversation.language_config import get_language_config

# Create prediction function
predict_fn = create_databricks_predict_fn()

# Verify endpoint is reachable
try:
    test_response = predict_fn("Say 'hello' in one word.", max_tokens=10)
    print(f"Endpoint test: {test_response}")
except Exception as e:
    print(f"Endpoint test failed: {e}")

# COMMAND ----------
# Create assistant
assistant = RealtimeAssistant(
    predict_fn=predict_fn,
    language=language,
    enable_tts=enable_tts,
    mock_tts=not enable_tts,  # Use mock if TTS disabled
)

config = get_language_config(language)
print(f"Assistant ready in {language.upper()} mode")
print(f"Greeting: {config['greeting']}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Test Conversation

# COMMAND ----------
# Start a new conversation
state = assistant.start_conversation(
    customer_context={"customer_id": "CUST001"}
)
print(f"Conversation started: {state.conversation_id}")

# COMMAND ----------
test_messages = [
    "Ciao, vorrei prenotare un taglio per domani",
    "Preferibilmente la mattina, verso le 10",
]

for msg in test_messages:
    print(f"\n{'='*50}")
    print(f"Customer: {msg}")
    
    result = assistant.process_text_turn(msg, customer_id="CUST001")
    
    if result.filler_text:
        print(f"[Filler]: {result.filler_text}")
    
    print(f"Assistant: {result.response_text}")
    print(f"Action: {result.action}")
    print(f"Time: {result.processing_time_ms:.0f}ms")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Voice Input (Optional)

# COMMAND ----------
# Process voice input if audio file is available
audio_path = os.getenv("AUDIO_INPUT_PATH", "")

if audio_path and Path(audio_path).exists():
    print(f"Processing audio: {audio_path}")
    
    result = assistant.process_voice_turn(audio_path, customer_id="CUST001")
    
    print(f"Transcribed: {result.user_text}")
    if result.filler_text:
        print(f"[Filler]: {result.filler_text}")
    print(f"Response: {result.response_text}")
    print(f"Action: {result.action}")
    
    if result.audio_output_path:
        print(f"Audio output: {result.audio_output_path}")
else:
    print("No audio file configured. Set AUDIO_INPUT_PATH to test voice input.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Conversation Summary

# COMMAND ----------
summary = assistant.get_conversation_summary()
print("Conversation Summary:")
for key, value in summary.items():
    print(f"  {key}: {value}")

# COMMAND ----------
# End conversation
farewell = assistant.end_conversation()
print(f"\n{farewell}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Interactive Mode (Text)
# MAGIC 
# MAGIC Use this cell to have an interactive text conversation.

# COMMAND ----------
# Uncomment to run interactive mode
# 
# assistant = RealtimeAssistant(
#     predict_fn=predict_fn,
#     language=language,
#     enable_tts=False,
# )
# assistant.start_conversation(customer_context={"customer_id": "CUST001"})
# 
# while True:
#     user_input = input("You: ")
#     if user_input.lower() in ["quit", "exit", "bye", "ciao"]:
#         print(assistant.end_conversation())
#         break
#     
#     result = assistant.process_text_turn(user_input)
#     if result.filler_text:
#         print(f"[{result.filler_text}]")
#     print(f"Assistant: {result.response_text}")

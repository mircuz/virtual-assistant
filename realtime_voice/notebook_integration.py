"""
Databricks Notebook Integration

This module provides the bridge between the Databricks notebook environment
and the real-time voice assistant components.

Usage in Databricks notebook:
    
    # COMMAND ----------
    # %pip install requests psycopg2-binary faster-whisper
    
    # COMMAND ----------
    import sys
    sys.path.insert(0, "/Workspace/Repos/your-repo/realtime_voice")
    
    from realtime_voice.notebook_integration import (
        setup_assistant,
        process_voice_input,
        process_text_input,
    )
    
    # Initialize
    assistant = setup_assistant()
    
    # Process voice
    result = process_voice_input(assistant, "/path/to/audio.wav")
    print(result.response_text)
    
    # Or process text
    result = process_text_input(assistant, "Vorrei prenotare un taglio per domani")
    print(result.response_text)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import requests


def load_env_file(env_path: str) -> None:
    """
    Load environment variables from a file.
    
    Args:
        env_path: Path to the .env file.
    """
    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")
    
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def create_databricks_predict_fn(
    host: str | None = None,
    token: str | None = None,
    endpoint: str | None = None,
) -> Callable[[str, int], str]:
    """
    Create a prediction function that calls Databricks Model Serving.
    
    Args:
        host: Databricks workspace URL.
        token: Databricks API token.
        endpoint: Model serving endpoint name.
    
    Returns:
        Function that takes (prompt, max_tokens) and returns response text.
    """
    host = host or os.getenv("DATABRICKS_HOST", "").rstrip("/")
    token = token or os.getenv("DATABRICKS_TOKEN")
    endpoint = endpoint or os.getenv("DATABRICKS_ENDPOINT", "personaplex-7b-endpoint")
    
    if not host:
        raise ValueError("DATABRICKS_HOST not configured")
    
    # Try to get token from notebook context if not provided
    if not token:
        try:
            # This works in Databricks notebooks
            from dbruntime.databricks_repl_context import get_context
            token = get_context().apiToken
        except Exception:
            pass
    
    if not token:
        raise ValueError("DATABRICKS_TOKEN not configured and no notebook token available")
    
    endpoint_url = f"{host}/serving-endpoints/{endpoint}/invocations"
    
    def predict(prompt: str, max_tokens: int = 512) -> str:
        """Call the Databricks model endpoint."""
        payload = {"prompt": prompt, "max_tokens": max_tokens}
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.post(endpoint_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle various response formats
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict) and "response" in first:
                return first["response"]
            return str(first)
        
        if "predictions" in data and data["predictions"]:
            pred = data["predictions"][0]
            if isinstance(pred, dict) and "response" in pred:
                return pred["response"]
            return str(pred)
        
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        
        raise RuntimeError(f"Unexpected model response shape: {data}")
    
    return predict


def setup_assistant(
    env_file: str | None = None,
    language: str | None = None,
    enable_tts: bool = True,
    mock_tts: bool = False,
):
    """
    Set up the real-time assistant for use in a Databricks notebook.
    
    Args:
        env_file: Path to environment file.
        language: Language code ("it").
        enable_tts: Whether to enable text-to-speech.
        mock_tts: Use mock TTS for testing.
    
    Returns:
        Configured RealtimeAssistant instance.
    """
    # Load environment if file provided
    if env_file:
        load_env_file(env_file)
    elif os.getenv("ENV_FILE"):
        load_env_file(os.getenv("ENV_FILE"))
    elif os.getenv("VOLUME_BASE"):
        volume_base = os.getenv("VOLUME_BASE").rstrip("/")
        load_env_file(f"{volume_base}/lakebase.env")
    
    # Import here to allow env setup first
    from .realtime_assistant import RealtimeAssistant
    
    # Create prediction function
    predict_fn = create_databricks_predict_fn()
    
    # Create assistant
    assistant = RealtimeAssistant(
        predict_fn=predict_fn,
        language=language,
        enable_tts=enable_tts,
        mock_tts=mock_tts,
    )
    
    return assistant


def process_voice_input(
    assistant,
    audio_path: str,
    customer_id: str | None = None,
):
    """
    Process voice input through the assistant.
    
    Args:
        assistant: RealtimeAssistant instance.
        audio_path: Path to audio file.
        customer_id: Optional customer ID.
    
    Returns:
        TurnResult with response.
    """
    return assistant.process_voice_turn(audio_path, customer_id=customer_id)


def process_text_input(
    assistant,
    text: str,
    customer_id: str | None = None,
):
    """
    Process text input through the assistant.
    
    Args:
        assistant: RealtimeAssistant instance.
        text: User text input.
        customer_id: Optional customer ID.
    
    Returns:
        TurnResult with response.
    """
    return assistant.process_text_turn(text, customer_id=customer_id)


# Example notebook usage
EXAMPLE_NOTEBOOK = '''
# Databricks notebook source
# MAGIC %md
# MAGIC # Real-Time Voice Assistant
# MAGIC 
# MAGIC Natural conversation for appointment booking (Italian-only).

# COMMAND ----------
# MAGIC %pip install requests psycopg2-binary faster-whisper torch

# COMMAND ----------
import sys
import os

# Add the realtime_voice package to path
# Adjust this path based on your repo location
sys.path.insert(0, "/Workspace/Repos/your-username/virtual-assistant")

# COMMAND ----------
from realtime_voice.notebook_integration import (
    setup_assistant,
    process_text_input,
    process_voice_input,
)

# COMMAND ----------
# Configure environment
dbutils.widgets.text("ENV_FILE", "/Volumes/mircom_test/assistant_mochi/data/lakebase.env")
dbutils.widgets.text("LANGUAGE", "it")

env_file = dbutils.widgets.get("ENV_FILE")
language = dbutils.widgets.get("LANGUAGE")

os.environ["ASSISTANT_LANGUAGE"] = language

# COMMAND ----------
# Initialize assistant
assistant = setup_assistant(
    env_file=env_file,
    language=language,
    enable_tts=True,  # Set to False for text-only testing
)

print(f"Assistant initialized in {language.upper()} mode")

# COMMAND ----------
# Test with text input
result = process_text_input(
    assistant,
    "Ciao, vorrei prenotare un taglio per domani mattina" if language == "it" 
    else "Hi, I'd like to book a haircut for tomorrow morning",
    customer_id="CUST001",
)

print(f"User: {result.user_text}")
print(f"Filler: {result.filler_text}")
print(f"Response: {result.response_text}")
print(f"Action: {result.action}")
print(f"Processing time: {result.processing_time_ms:.0f}ms")

# COMMAND ----------
# Test with voice input (if you have an audio file)
# audio_path = "/Volumes/mircom_test/assistant_mochi/data/audio/test.wav"
# result = process_voice_input(assistant, audio_path)
# print(result.response_text)

# COMMAND ----------
# End conversation
farewell = assistant.end_conversation()
print(farewell)
'''


def print_example_notebook():
    """Print example notebook code for copy-paste."""
    print(EXAMPLE_NOTEBOOK)

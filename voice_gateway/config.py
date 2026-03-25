"""Voice Gateway configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    booking_engine_url: str = "http://localhost:8000"
    databricks_host: str = ""
    databricks_token: str = ""
    stt_endpoint: str = "whisper-stt-endpoint"
    tts_endpoint: str = "kokoro-tts-endpoint"
    intent_llm_endpoint: str = "databricks-meta-llama-3-1-8b-instruct"
    response_llm_endpoint: str = "databricks-meta-llama-3-3-70b-instruct"

    model_config = {"env_prefix": ""}

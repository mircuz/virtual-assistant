"""Voice Gateway configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    booking_engine_url: str = "http://localhost:8000"
    databricks_host: str = ""
    databricks_token: str = ""
    stt_endpoint: str = ""
    tts_url: str = ""
    llm_endpoint: str = "databricks-claude-haiku-4-5"

    model_config = {"env_prefix": ""}

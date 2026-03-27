"""Voice Gateway configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    booking_engine_url: str = "http://localhost:8000"
    databricks_host: str = ""
    databricks_token: str = ""
    openai_key: str = ""

    model_config = {"env_prefix": ""}

"""Voice Gateway configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


# Load .env file
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)


class Settings(BaseSettings):
    booking_engine_url: str = "http://localhost:8000"
    databricks_host: str = ""
    databricks_token: str = ""
    openai_key: str = ""

    model_config = {"env_prefix": ""}

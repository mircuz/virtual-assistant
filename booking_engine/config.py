"""Booking Engine configuration from environment variables."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


# Load .env file
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)


class Settings(BaseSettings):
    databricks_server_hostname: str = ""
    databricks_http_path: str = ""
    databricks_token: str = ""
    databricks_catalog: str = "mircom_test"
    databricks_schema: str = "virtual_assistant"

    @property
    def table_prefix(self) -> str:
        return f"{self.databricks_catalog}.{self.databricks_schema}"

    model_config = {"env_prefix": ""}

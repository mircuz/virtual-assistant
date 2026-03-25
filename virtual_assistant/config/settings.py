"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Databricks
    databricks_host: str = ""
    databricks_token: str = ""
    databricks_endpoint: str = "personaplex-7b-endpoint"
    databricks_tts_endpoint: str = "kokoro-tts-endpoint"

    # Lakebase
    lakebase_host: str = ""
    lakebase_port: int = 5432
    lakebase_db: str = "databricks_postgres"
    lakebase_user: str = ""
    lakebase_password: str = ""
    lakebase_sslmode: str = "require"
    lakebase_schema: str = "assistant_mochi"

    # Voice
    tts_voice: str = "af_sky"
    stt_model: str = "base"

    # Paths
    volume_base: str = "/tmp/virtual_assistant"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            databricks_host=os.getenv("DATABRICKS_HOST", ""),
            databricks_token=os.getenv("DATABRICKS_TOKEN", ""),
            databricks_endpoint=os.getenv("DATABRICKS_ENDPOINT", "personaplex-7b-endpoint"),
            databricks_tts_endpoint=os.getenv("DATABRICKS_TTS_ENDPOINT", "kokoro-tts-endpoint"),
            lakebase_host=os.getenv("LAKEBASE_HOST", ""),
            lakebase_port=int(os.getenv("LAKEBASE_PORT", "5432")),
            lakebase_db=os.getenv("LAKEBASE_DB", "databricks_postgres"),
            lakebase_user=os.getenv("LAKEBASE_USER", ""),
            lakebase_password=os.getenv("LAKEBASE_PASSWORD", ""),
            lakebase_sslmode=os.getenv("LAKEBASE_SSLMODE", "require"),
            lakebase_schema=os.getenv("LAKEBASE_SCHEMA", "assistant_mochi"),
            tts_voice=os.getenv("TTS_VOICE", "af_sky"),
            stt_model=os.getenv("STT_MODEL", "base"),
            volume_base=os.getenv("VOLUME_BASE", "/tmp/virtual_assistant"),
        )

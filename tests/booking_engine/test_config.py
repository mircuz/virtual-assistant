import os
from unittest.mock import patch

def test_settings_from_env():
    env = {
        "LAKEBASE_HOST": "test-host",
        "LAKEBASE_PORT": "5432",
        "LAKEBASE_DB": "testdb",
        "LAKEBASE_USER": "testuser",
        "LAKEBASE_PASSWORD": "testpass",
        "LAKEBASE_SCHEMA": "hair_salon",
    }
    with patch.dict(os.environ, env, clear=False):
        from booking_engine.config import Settings
        s = Settings()
        assert s.lakebase_host == "test-host"
        assert s.lakebase_port == 5432
        assert s.lakebase_schema == "hair_salon"

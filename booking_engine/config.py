"""Booking Engine configuration from environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    lakebase_host: str
    lakebase_port: int = 5432
    lakebase_db: str = "databricks_postgres"
    lakebase_user: str = "authenticator"
    lakebase_password: str = ""
    lakebase_schema: str = "hair_salon"
    lakebase_sslmode: str = "require"

    @property
    def dsn(self) -> str:
        return (
            f"host={self.lakebase_host} port={self.lakebase_port} "
            f"dbname={self.lakebase_db} user={self.lakebase_user} "
            f"password={self.lakebase_password} sslmode={self.lakebase_sslmode}"
        )

    model_config = {"env_prefix": ""}

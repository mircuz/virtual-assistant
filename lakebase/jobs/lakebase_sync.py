from __future__ import annotations

import json
import os
from pathlib import Path

from pyspark.sql import SparkSession


def _load_env(env_path: str | None) -> None:
    if not env_path:
        return

    path = Path(env_path)
    if not path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _load_config(config_path: str, spark: SparkSession) -> dict:
    if config_path.startswith("volume:/"):
        config_path = "/Volumes/" + config_path.replace("volume:/", "", 1).lstrip("/")

    if config_path.startswith("/Volumes/"):
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return json.loads(path.read_text())

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return json.loads(path.read_text())


def _jdbc_options() -> dict:
    return {
        "url": os.environ["LAKEBASE_JDBC_URL"],
        "user": os.environ["LAKEBASE_USER"],
        "password": os.environ["LAKEBASE_PASSWORD"],
        "driver": os.getenv("LAKEBASE_JDBC_DRIVER", "org.postgresql.Driver"),
    }


def main() -> None:
    spark = SparkSession.builder.getOrCreate()
    env_path = os.getenv("ENV_FILE")
    if not env_path:
        volume_base = os.getenv("VOLUME_BASE")
        if volume_base:
            env_path = str(Path(volume_base.rstrip("/")) / "lakebase.env")
    if not env_path:
        raise RuntimeError(
            "Missing ENV_FILE. Set ENV_FILE to your Volume env path "
            "or set VOLUME_BASE to the Volume root."
        )
    _load_env(env_path)

    config_path = os.getenv("TABLE_SYNC_CONFIG")
    if not config_path and env_path:
        env_dir = str(Path(env_path).parent)
        config_path = str(Path(env_dir) / "table_sync_config.json")
    if not config_path:
        raise RuntimeError(
            "Missing TABLE_SYNC_CONFIG. Set it in your env file or job env vars."
        )
    config = _load_config(config_path, spark)

    catalog = config["source_catalog"]
    schema = config["source_schema"]
    target_schema = config["target_schema"]
    tables = config["tables"]

    options = _jdbc_options()
    for table in tables:
        source_table = f"{catalog}.{schema}.{table}"
        target_table = f"{target_schema}.{table}"

        df = spark.read.table(source_table)
        (
            df.write.format("jdbc")
            .mode("overwrite")
            .options(**options)
            .option("dbtable", target_table)
            .save()
        )


if __name__ == "__main__":
    main()

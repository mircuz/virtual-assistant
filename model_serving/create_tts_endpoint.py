"""
Create (or update) a Databricks Model Serving endpoint for Kokoro TTS.

Run this after log_kokoro_tts.py has registered the model in Unity Catalog.
Requires: `pip install databricks-sdk`
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput,
    ServedEntityInput,
)

ENDPOINT_NAME = "kokoro-tts-endpoint"
MODEL_NAME = "users.mirco_meazzo.kokoro_tts"
MODEL_VERSION = 1  # bump after re-logging

w = WorkspaceClient()

# Check if endpoint already exists
existing = {ep.name for ep in w.serving_endpoints.list()}

config = EndpointCoreConfigInput(
    served_entities=[
        ServedEntityInput(
            entity_name=MODEL_NAME,
            entity_version=str(MODEL_VERSION),
            workload_size="Small",      # Small / Medium / Large
            workload_type="CPU",  # CPU — no GPU available on this workspace
            scale_to_zero_enabled=True,
        )
    ]
)

if ENDPOINT_NAME in existing:
    print(f"Updating endpoint '{ENDPOINT_NAME}' ...")
    w.serving_endpoints.update_config(name=ENDPOINT_NAME, served_entities=config.served_entities)
else:
    print(f"Creating endpoint '{ENDPOINT_NAME}' ...")
    w.serving_endpoints.create(name=ENDPOINT_NAME, config=config)

print("Done. Endpoint will be ready in a few minutes.")
print(f"URL: https://{w.config.host}/serving-endpoints/{ENDPOINT_NAME}/invocations")

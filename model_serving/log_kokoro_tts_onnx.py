"""
Log Kokoro TTS (ONNX variant) as an MLflow pyfunc model.
Uses kokoro-onnx instead of kokoro to avoid PyTorch dependency.

Run on a Databricks cluster with:
  pip install kokoro-onnx soundfile numpy
"""

import base64
import io

import mlflow
import numpy as np
import pandas as pd
import soundfile as sf
from mlflow.models.signature import ModelSignature
from mlflow.types.schema import ColSpec, Schema

mlflow.set_registry_uri("databricks-uc")
CATALOG = "users"
SCHEMA = "mirco_meazzo"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.kokoro_tts"


class KokoroTTSModel(mlflow.pyfunc.PythonModel):
    """MLflow pyfunc wrapper around Kokoro TTS (ONNX variant)."""

    SAMPLE_RATE = 24_000

    def load_context(self, context: mlflow.pyfunc.PythonModelContext) -> None:
        import kokoro_onnx
        self._model = kokoro_onnx.Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        results = []
        for _, row in model_input.iterrows():
            text = str(row["text"])
            voice = str(row.get("voice", "if_sara"))
            lang = str(row.get("language", "i"))

            audio, sr = self._model.create(text, voice=voice, lang=lang, speed=1.0)

            buf = io.BytesIO()
            sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            results.append(b64)

        return pd.DataFrame({"audio_base64": results})


input_schema = Schema([
    ColSpec("string", "text"),
    ColSpec("string", "voice"),
    ColSpec("string", "language"),
])
output_schema = Schema([ColSpec("string", "audio_base64")])
signature = ModelSignature(inputs=input_schema, outputs=output_schema)

pip_requirements = [
    "kokoro-onnx",
    "soundfile",
    "numpy",
    "pandas",
    "onnxruntime",
]

input_example = pd.DataFrame([{
    "text": "Buongiorno, come posso aiutarla oggi?",
    "voice": "if_sara",
    "language": "i",
}])

with mlflow.start_run(run_name="kokoro-tts-onnx-registration") as run:
    model_info = mlflow.pyfunc.log_model(
        artifact_path="kokoro_tts",
        python_model=KokoroTTSModel(),
        signature=signature,
        input_example=input_example,
        pip_requirements=pip_requirements,
        registered_model_name=MODEL_NAME,
    )
    print(f"Model URI : {model_info.model_uri}")
    print(f"Registered: {MODEL_NAME}")

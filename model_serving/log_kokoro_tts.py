"""
Log Kokoro TTS (hexgrad/Kokoro-82M) as an MLflow pyfunc model
and register it in Unity Catalog.

Run this script on a Databricks cluster (CPU or GPU) with:
  - Runtime 15.4 ML+
  - `pip install kokoro>=0.9.4 soundfile misaki[en,it,zh,ja]`
  - `sudo apt-get install -y espeak-ng`  (already present on most ML runtimes)

The registered model will be at: users.mirco_meazzo.kokoro_tts
"""

import base64
import io

import mlflow
import numpy as np
import pandas as pd
import soundfile as sf
from mlflow.models.signature import ModelSignature
from mlflow.types.schema import ColSpec, Schema

# ---------------------------------------------------------------------------
# 1.  Unity Catalog registry setup
# ---------------------------------------------------------------------------
mlflow.set_registry_uri("databricks-uc")
CATALOG = "users"
SCHEMA = "mirco_meazzo"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.kokoro_tts"

# ---------------------------------------------------------------------------
# 2.  Define the pyfunc wrapper
# ---------------------------------------------------------------------------

class KokoroTTSModel(mlflow.pyfunc.PythonModel):
    """MLflow pyfunc wrapper around Kokoro TTS.

    Accepts JSON rows with:
        text     (str)  – text to synthesise
        voice    (str)  – voice id, e.g. "if_sara", "im_nicola", "af_heart"
        language (str)  – language code: "i" for Italian, "a" for American English, etc.

    Returns a DataFrame with a single column ``audio_base64`` containing
    base64-encoded 24 kHz mono WAV.
    """

    SAMPLE_RATE = 24_000

    # -- lifecycle -----------------------------------------------------------

    def load_context(self, context: mlflow.pyfunc.PythonModelContext) -> None:
        """Called once when the serving container starts."""
        from kokoro import KPipeline  # import here so deps resolve at load time

        # Pre-warm pipelines for the languages we care about.
        # KPipeline lazily downloads the model from HuggingFace on first use.
        # We keep a dict so we can serve multiple languages from one endpoint.
        self._pipelines: dict = {}

        # Pre-load Italian (primary use-case) so first request is fast.
        self._pipelines["i"] = KPipeline(lang_code="i")

    # -- prediction ----------------------------------------------------------

    def predict(
        self,
        context: mlflow.pyfunc.PythonModelContext,
        model_input: pd.DataFrame,
    ) -> pd.DataFrame:
        from kokoro import KPipeline

        results: list[str] = []

        for _, row in model_input.iterrows():
            text = str(row["text"])
            voice = str(row.get("voice", "if_sara"))
            lang = str(row.get("language", "i"))

            # Lazily create pipeline for unseen language codes
            if lang not in self._pipelines:
                self._pipelines[lang] = KPipeline(lang_code=lang)

            pipeline = self._pipelines[lang]

            # Generate audio – concatenate all chunks
            chunks: list[np.ndarray] = []
            for _graphemes, _phonemes, audio_chunk in pipeline(
                text, voice=voice, speed=1.0
            ):
                if audio_chunk is not None:
                    chunks.append(audio_chunk)

            if not chunks:
                results.append("")
                continue

            audio = np.concatenate(chunks)

            # Encode as WAV -> base64
            buf = io.BytesIO()
            sf.write(buf, audio, self.SAMPLE_RATE, format="WAV", subtype="PCM_16")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            results.append(b64)

        return pd.DataFrame({"audio_base64": results})


# ---------------------------------------------------------------------------
# 3.  MLflow model signature
# ---------------------------------------------------------------------------
input_schema = Schema(
    [
        ColSpec("string", "text"),
        ColSpec("string", "voice"),
        ColSpec("string", "language"),
    ]
)
output_schema = Schema([ColSpec("string", "audio_base64")])
signature = ModelSignature(inputs=input_schema, outputs=output_schema)

# ---------------------------------------------------------------------------
# 4.  Pip requirements
#     - kokoro pulls in torch, misaki (G2P), and the ONNX/StyleTTS internals
#     - soundfile is needed for WAV encoding
#     - espeak-ng is a *system* dep – Databricks ML runtimes include it;
#       if missing, add a custom Docker layer or init script.
# ---------------------------------------------------------------------------
pip_requirements = [
    "kokoro>=0.9.4",
    "soundfile",
    "misaki[en,it,zh,ja]",
    "numpy",
    "pandas",
]

# ---------------------------------------------------------------------------
# 5.  Log and register the model
# ---------------------------------------------------------------------------
input_example = pd.DataFrame(
    [
        {
            "text": "Buongiorno, come posso aiutarla oggi?",
            "voice": "if_sara",
            "language": "i",
        }
    ]
)

with mlflow.start_run(run_name="kokoro-tts-registration") as run:
    model_info = mlflow.pyfunc.log_model(
        artifact_path="kokoro_tts",
        python_model=KokoroTTSModel(),
        signature=signature,
        input_example=input_example,
        pip_requirements=pip_requirements,
        registered_model_name=MODEL_NAME,
        # Extra metadata visible in UC
        metadata={
            "model_family": "kokoro-82m",
            "sample_rate": 24000,
            "supported_languages": "a,b,e,f,h,i,j,p,z",
            "italian_voices": "if_sara,im_nicola",
        },
    )

    print(f"Model URI : {model_info.model_uri}")
    print(f"Run ID    : {run.info.run_id}")
    print(f"Registered: {MODEL_NAME}")

# ---------------------------------------------------------------------------
# 6.  (Optional) Quick local sanity check
#     Uncomment to test locally before deploying to Model Serving.
# ---------------------------------------------------------------------------
# loaded = mlflow.pyfunc.load_model(model_info.model_uri)
# out = loaded.predict(input_example)
# print(f"Audio base64 length: {len(out['audio_base64'][0])}")

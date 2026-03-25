"""
Streaming Speech-to-Text with Voice Activity Detection

Provides real-time transcription with VAD for detecting speech boundaries.
Italian only.
"""

from __future__ import annotations

import io
import os
import time
import wave
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Generator

import numpy as np


class SpeechState(Enum):
    """Current state of speech detection."""

    SILENCE = "silence"
    SPEAKING = "speaking"
    SPEECH_END = "speech_end"


@dataclass
class TranscriptionEvent:
    """Event from the transcription pipeline."""

    event_type: str  # "partial", "final", "speech_start", "speech_end"
    text: str
    confidence: float
    timestamp: float
    language: str


@dataclass
class VADResult:
    """Result from voice activity detection."""

    is_speech: bool
    confidence: float
    state: SpeechState


class StreamingTranscriber:
    """
    Streaming speech-to-text with voice activity detection.

    Processes audio chunks in real-time, detecting speech boundaries
    and providing transcriptions as speech segments complete.
    """

    def __init__(
        self,
        language: str = "it",
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        vad_threshold: float = 0.5,
        silence_duration_threshold: float = 0.8,
    ):
        """
        Initialize the streaming transcriber.

        Args:
            language: Language code ("it").
            model_size: Whisper model size. Defaults to STT_MODEL env var or "base".
            device: Device to use. Defaults to STT_DEVICE env var or "cpu".
            compute_type: Compute type. Defaults to STT_COMPUTE_TYPE env var or "int8".
            vad_threshold: VAD speech detection threshold (0-1).
            silence_duration_threshold: Seconds of silence to mark speech end.
        """
        self.language = language
        self.model_size = model_size or os.getenv("STT_MODEL", "base")
        self.device = device or os.getenv("STT_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("STT_COMPUTE_TYPE", "int8")
        self.vad_threshold = vad_threshold
        self.silence_duration_threshold = silence_duration_threshold

        # Lazy-loaded models
        self._whisper_model = None
        self._vad_model = None

        # State tracking
        self._audio_buffer: list[np.ndarray] = []
        self._speech_state = SpeechState.SILENCE
        self._silence_start_time: float | None = None
        self._speech_start_time: float | None = None

    @property
    def whisper_model(self):
        """Lazy load Whisper model."""
        if self._whisper_model is None:
            from faster_whisper import WhisperModel

            self._whisper_model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._whisper_model

    @property
    def vad_model(self):
        """Lazy load VAD model (Silero)."""
        if self._vad_model is None:
            try:
                import torch

                self._vad_model, _ = torch.hub.load(
                    repo_or_dir="snakers4/silero-vad",
                    model="silero_vad",
                    force_reload=False,
                    trust_repo=True,
                )
            except Exception as e:
                print(f"Warning: Could not load Silero VAD: {e}")
                self._vad_model = None
        return self._vad_model

    def detect_voice_activity(
        self, audio_chunk: np.ndarray, sample_rate: int = 16000
    ) -> VADResult:
        """
        Detect voice activity in an audio chunk.

        Args:
            audio_chunk: Audio samples as numpy array.
            sample_rate: Sample rate in Hz.

        Returns:
            VADResult with speech detection status.
        """
        if self.vad_model is None:
            # Fallback: simple energy-based detection
            energy = np.sqrt(np.mean(audio_chunk**2))
            is_speech = energy > 0.01
            return VADResult(
                is_speech=is_speech,
                confidence=min(energy * 10, 1.0),
                state=self._speech_state,
            )

        try:
            import torch

            audio_tensor = torch.from_numpy(audio_chunk).float()
            speech_prob = self.vad_model(audio_tensor, sample_rate).item()
            is_speech = speech_prob > self.vad_threshold

            current_time = time.time()

            if is_speech:
                if self._speech_state == SpeechState.SILENCE:
                    self._speech_state = SpeechState.SPEAKING
                    self._speech_start_time = current_time
                self._silence_start_time = None
            else:
                if self._speech_state == SpeechState.SPEAKING:
                    if self._silence_start_time is None:
                        self._silence_start_time = current_time
                    elif (
                        current_time - self._silence_start_time
                        > self.silence_duration_threshold
                    ):
                        self._speech_state = SpeechState.SPEECH_END

            return VADResult(
                is_speech=is_speech,
                confidence=speech_prob,
                state=self._speech_state,
            )
        except Exception as e:
            print(f"VAD error: {e}")
            return VADResult(
                is_speech=False, confidence=0.0, state=self._speech_state
            )

    def process_chunk(
        self,
        audio_chunk: np.ndarray,
        sample_rate: int = 16000,
    ) -> TranscriptionEvent | None:
        """
        Process an audio chunk and return transcription event if speech ends.

        Args:
            audio_chunk: Audio samples as numpy array.
            sample_rate: Sample rate in Hz.

        Returns:
            TranscriptionEvent if speech segment completed, None otherwise.
        """
        vad_result = self.detect_voice_activity(audio_chunk, sample_rate)

        if vad_result.is_speech or self._speech_state == SpeechState.SPEAKING:
            self._audio_buffer.append(audio_chunk)

        if vad_result.state == SpeechState.SPEECH_END and self._audio_buffer:
            full_audio = np.concatenate(self._audio_buffer)
            text = self._transcribe_array(full_audio, sample_rate)

            event = TranscriptionEvent(
                event_type="final",
                text=text,
                confidence=vad_result.confidence,
                timestamp=time.time(),
                language=self.language,
            )

            self._audio_buffer = []
            self._speech_state = SpeechState.SILENCE
            self._silence_start_time = None

            return event

        return None

    def _transcribe_array(self, audio: np.ndarray, sample_rate: int) -> str:
        """Transcribe audio array using Whisper."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

            if audio.dtype != np.int16:
                audio = (audio * 32767).astype(np.int16)

            with wave.open(temp_path, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(audio.tobytes())

        try:
            text = self.transcribe(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

        return text

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file.

        Returns:
            Transcription text.
        """
        segments, info = self.whisper_model.transcribe(
            audio_path,
            language=self.language,
            task="transcribe",
            beam_size=5,
            vad_filter=True,
        )

        return "".join(segment.text for segment in segments).strip()

    def reset(self) -> None:
        """Reset the transcriber state."""
        self._audio_buffer = []
        self._speech_state = SpeechState.SILENCE
        self._silence_start_time = None
        self._speech_start_time = None


# Global transcriber instance
_transcriber: StreamingTranscriber | None = None


def get_transcriber(language: str | None = None) -> StreamingTranscriber:
    """Get or create a transcriber instance."""
    global _transcriber

    lang = language or os.getenv("ASSISTANT_LANGUAGE", "it")

    if _transcriber is None or _transcriber.language != lang:
        _transcriber = StreamingTranscriber(language=lang)

    return _transcriber


def transcribe_audio(audio_path: str, language: str | None = None) -> str:
    """
    Convenience function to transcribe an audio file.

    Args:
        audio_path: Path to audio file.
        language: Language code. Defaults to env config.

    Returns:
        Transcription text.
    """
    transcriber = get_transcriber(language)
    return transcriber.transcribe(audio_path)

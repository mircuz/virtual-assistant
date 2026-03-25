"""
Language configuration for Italian-only voice assistant.
"""

import os
from typing import TypedDict


class LanguageConfig(TypedDict):
    """Configuration for a supported language."""
    code: str
    whisper_language: str
    locale: str
    system_prompt_prefix: str
    greeting: str
    farewell: str
    error_message: str


SUPPORTED_LANGUAGES = {"it"}

LANGUAGE_CONFIGS: dict[str, LanguageConfig] = {
    "it": {
        "code": "it",
        "whisper_language": "it",
        "locale": "it-IT",
        "system_prompt_prefix": (
            "Sei un assistente per appuntamenti di un'attività commerciale. "
            "Rispondi in italiano naturale e colloquiale. "
            "Sii cordiale e professionale."
        ),
        "greeting": "Buongiorno! Come posso aiutarla?",
        "farewell": "Grazie per aver chiamato. Buona giornata!",
        "error_message": "Mi scusi, non ho capito. Può ripetere per favore?",
    },
}


def get_language_config(language: str | None = None) -> LanguageConfig:
    """
    Get language configuration.
    
    Args:
        language: Language code ("it"). If None, reads from ASSISTANT_LANGUAGE env var.
    
    Returns:
        LanguageConfig for the specified language, defaults to Italian if not found.
    """
    if language is None:
        language = os.getenv("ASSISTANT_LANGUAGE", "it").lower().strip()

    if language not in SUPPORTED_LANGUAGES:
        print(f"Warning: Unsupported language '{language}', defaulting to Italian")
        language = "it"
    
    return LANGUAGE_CONFIGS[language]


def get_current_language() -> str:
    """Get the currently configured language code."""
    return os.getenv("ASSISTANT_LANGUAGE", "it").lower().strip()

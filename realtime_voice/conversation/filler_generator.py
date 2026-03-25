"""
Filler Generator

Generates natural, human-like filler responses to maintain conversation flow
while waiting for agent results. Italian only.
"""

import random
from typing import Literal

from .language_config import get_language_config


FillerType = Literal[
    "thinking",
    "confirming", 
    "waiting",
    "clarifying",
    "acknowledging",
    "transitioning",
]


# Filler responses (Italian only)
FILLER_RESPONSES: dict[str, dict[FillerType, list[str]]] = {
    "it": {
        "thinking": [
            "Un attimo, controllo subito...",
            "Fammi verificare...",
            "Vediamo un po'...",
            "Mi dia un momento...",
            "Controllo immediatamente...",
        ],
        "confirming": [
            "Perfetto.",
            "Capito.",
            "Va bene.",
            "Certamente.",
            "D'accordo.",
        ],
        "waiting": [
            "Sto verificando in questo momento.",
            "Solo un secondo...",
            "Un attimo ancora...",
            "Quasi fatto...",
            "Sto ancora controllando...",
        ],
        "clarifying": [
            "Per essere sicuro di aver capito...",
            "Quindi sta cercando...",
            "Mi faccia confermare...",
            "Se ho capito bene...",
        ],
        "acknowledging": [
            "Capisco.",
            "Va bene.",
            "Certo.",
            "Sì sì.",
            "Certamente.",
        ],
        "transitioning": [
            "Bene, allora...",
            "Perfetto, dunque...",
            "Va bene, vediamo...",
            "Ottimo, quindi...",
        ],
    },
}


# Longer fillers for extended waits (> 3 seconds expected)
EXTENDED_FILLERS: dict[str, list[str]] = {
    "it": [
        "Sto controllando la nostra disponibilità. Ci vorrà solo un momento.",
        "Sto cercando nella nostra agenda. Quasi fatto.",
        "Sto verificando gli appuntamenti disponibili. Solo qualche secondo ancora.",
    ],
}


class FillerGenerator:
    """
    Generates contextually appropriate filler responses.
    
    Fillers help maintain natural conversation flow by:
    - Acknowledging user input immediately
    - Filling silence while waiting for agent results
    - Providing thinking sounds/phrases like humans do
    """

    def __init__(self, language: str | None = None):
        """
        Initialize the filler generator.
        
        Args:
            language: Language code ("it"). Defaults to env config.
        """
        config = get_language_config(language)
        self.language = config["code"]
        self._last_fillers: dict[FillerType, str] = {}

    def generate(
        self,
        filler_type: FillerType,
        avoid_repeat: bool = True,
    ) -> str:
        """
        Generate a filler response.
        
        Args:
            filler_type: Type of filler to generate.
            avoid_repeat: If True, avoid repeating the last filler of this type.
        
        Returns:
            A natural filler phrase in the configured language.
        """
        fillers = FILLER_RESPONSES["it"]
        options = fillers.get(filler_type, fillers["thinking"])
        
        if avoid_repeat and filler_type in self._last_fillers:
            last = self._last_fillers[filler_type]
            options = [f for f in options if f != last] or options
        
        selected = random.choice(options)
        self._last_fillers[filler_type] = selected
        return selected

    def generate_for_wait(self, expected_wait_seconds: float) -> str:
        """
        Generate a filler appropriate for the expected wait time.
        
        Args:
            expected_wait_seconds: How long we expect to wait for agent response.
        
        Returns:
            A filler phrase appropriate for the wait duration.
        """
        if expected_wait_seconds > 3.0:
            extended = EXTENDED_FILLERS["it"]
            return random.choice(extended)
        elif expected_wait_seconds > 1.5:
            return self.generate("thinking")
        else:
            return self.generate("acknowledging")

    def generate_sequence(
        self,
        filler_types: list[FillerType],
        separator: str = " ",
    ) -> str:
        """
        Generate a sequence of fillers joined together.
        
        Useful for longer pauses where multiple fillers feel natural.
        
        Args:
            filler_types: List of filler types to combine.
            separator: String to join fillers with.
        
        Returns:
            Combined filler string.
        """
        fillers = [self.generate(ft) for ft in filler_types]
        return separator.join(fillers)

    def get_thinking_filler(self) -> str:
        """Quick access to a thinking filler."""
        return self.generate("thinking")

    def get_confirmation_filler(self) -> str:
        """Quick access to a confirmation filler."""
        return self.generate("confirming")

    def get_wait_filler(self) -> str:
        """Quick access to a waiting filler."""
        return self.generate("waiting")


def get_filler(
    filler_type: FillerType,
    language: str | None = None,
) -> str:
    """
    Convenience function to get a single filler.
    
    Args:
        filler_type: Type of filler to generate.
        language: Language code. Defaults to env config.
    
    Returns:
        A natural filler phrase.
    """
    generator = FillerGenerator(language)
    return generator.generate(filler_type)

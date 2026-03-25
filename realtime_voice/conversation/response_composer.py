"""
Response Composer

Generates natural responses that incorporate agent results into the conversation.
Handles multilingual response generation with appropriate prompts.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .language_config import get_language_config
from .state_manager import ConversationState, AgentTask


# Response generation prompts (Italian only)
RESPONSE_PROMPTS: dict[str, str] = {
    "it": """Sei un assistente per appuntamenti nel mezzo di una telefonata.
Il cliente ha chiesto: {user_utterance}
Hai detto che avresti controllato. Ora hai la risposta: {result}

Storico conversazione:
{history}

Genera una risposta naturale in italiano che:
- Fluisce naturalmente dalla tua affermazione precedente
- Presenta le informazioni in modo colloquiale (non come leggere una lista)
- Suona come una persona vera, non un robot
- È concisa ma completa
- Se ci sono più opzioni, presentale chiaramente

NON dire cose come "Ho trovato", "Il sistema mostra", "Secondo i nostri dati".
Invece, parla naturalmente come: "Abbiamo...", "C'è...", "Potrebbe venire alle..."

Risposta:""",
}


# Prompts for when agent found no results (Italian only)
NO_RESULTS_PROMPTS: dict[str, str] = {
    "it": """Sei un assistente per appuntamenti nel mezzo di una telefonata.
Il cliente ha chiesto: {user_utterance}
Purtroppo non ci sono opzioni disponibili che corrispondano alla richiesta.

Storico conversazione:
{history}

Genera una risposta naturale e empatica in italiano che:
- Si scusa brevemente per la mancanza di disponibilità
- Suggerisce alternative se possibile (orario diverso, giorno diverso, ecc.)
- Offre di aiutare a trovare un'altra soluzione
- Suona come una persona vera, non un robot

Risposta:""",
}


# Prompts for successful booking confirmation (Italian only)
BOOKING_SUCCESS_PROMPTS: dict[str, str] = {
    "it": """Sei un assistente per appuntamenti che conferma una prenotazione riuscita.
Dettagli della prenotazione: {result}

Storico conversazione:
{history}

Genera una conferma naturale in italiano che:
- Conferma che l'appuntamento è stato prenotato
- Ripete i dettagli chiave (data, ora, servizio)
- Ringrazia il cliente
- Chiede se c'è altro di cui hanno bisogno

Risposta:""",
}


class ResponseComposer:
    """
    Composes natural responses incorporating agent results.
    
    Uses LLM to generate human-like responses based on:
    - Agent results
    - Conversation history
    - Customer's original request
    """

    def __init__(
        self,
        predict_fn: Callable[[str, int], str],
        language: str | None = None,
    ):
        """
        Initialize the response composer.
        
        Args:
            predict_fn: Function to call LLM (prompt, max_tokens) -> response.
            language: Language code ("it"). Defaults to env config.
        """
        self.predict = predict_fn
        config = get_language_config(language)
        self.language = config["code"]

    def compose_agent_response(
        self,
        conv_state: ConversationState,
        task: AgentTask,
        max_tokens: int = 256,
    ) -> str:
        """
        Compose a natural response for an agent task result.
        
        Args:
            conv_state: Current conversation state.
            task: Completed agent task with results.
            max_tokens: Maximum tokens for response.
        
        Returns:
            Natural language response incorporating the agent result.
        """
        result = task.result
        history = conv_state.format_history_for_prompt(max_turns=6)
        user_utterance = conv_state.last_user_utterance

        # Determine which prompt to use based on action and result
        if task.action == "book_appointment":
            if result and result.get("rows_affected", 0) > 0:
                prompt_template = BOOKING_SUCCESS_PROMPTS["it"]
            else:
                prompt_template = NO_RESULTS_PROMPTS["it"]
        elif task.action == "check_availability":
            if result and len(result) > 0:
                prompt_template = RESPONSE_PROMPTS["it"]
            else:
                prompt_template = NO_RESULTS_PROMPTS["it"]
        else:
            prompt_template = RESPONSE_PROMPTS["it"]

        # Format the prompt
        prompt = prompt_template.format(
            user_utterance=user_utterance,
            result=json.dumps(result, default=str, ensure_ascii=False),
            history=history,
        )

        response = self.predict(prompt, max_tokens)
        return self._clean_response(response)

    def compose_error_response(
        self,
        conv_state: ConversationState,
        error_message: str,
    ) -> str:
        """
        Compose a natural response for an error situation.
        
        Args:
            conv_state: Current conversation state.
            error_message: Technical error message.
        
        Returns:
            User-friendly error response.
        """
        error_responses = [
            "Mi scusi, sto avendo qualche difficoltà al momento. "
            "Possiamo riprovare?",
            "Mi scuso, qualcosa non ha funzionato. "
            "Riprovo subito.",
        ]
        import random
        return random.choice(error_responses)

    def compose_clarification_request(
        self,
        conv_state: ConversationState,
        missing_fields: list[str],
    ) -> str:
        """
        Compose a natural request for missing information.
        
        Args:
            conv_state: Current conversation state.
            missing_fields: List of fields we need from the user.
        
        Returns:
            Natural clarification request.
        """
        clarification_prompts = {
            "service_id": "Quale servizio vorrebbe prenotare?",
            "slot_id": "Quale orario preferisce?",
            "start_date": "Per quale giorno sarebbe?",
            "end_date": "E fino a quando devo controllare la disponibilità?",
            "customer_id": "Potrei avere il suo nome o codice cliente?",
        }
        
        # Get the first missing field's clarification
        for field in missing_fields:
            if field in clarification_prompts:
                return clarification_prompts[field]
        
        # Generic fallback
        return "Potrebbe darmi qualche dettaglio in più?"

    def _clean_response(self, response: str) -> str:
        """Clean up LLM response text."""
        # Remove common prefixes the LLM might add
        prefixes_to_remove = [
            "Response:",
            "Risposta:",
            "Assistant:",
            "Assistente:",
        ]
        
        text = response.strip()
        for prefix in prefixes_to_remove:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        
        return text

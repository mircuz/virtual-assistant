"""
Intent Router

Routes user utterances to the appropriate agent based on intent detection.
Uses LLM to extract structured intent from natural language.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from .conversation.language_config import get_language_config
from .agents.availability_agent import AvailabilityAgent


# Router prompt template (Italian only)
ROUTER_PROMPTS: dict[str, str] = {
    "it": """Sei un router di intenti per un assistente vocale per appuntamenti.
Analizza la richiesta del cliente ed estrai l'intento.

Azioni disponibili:
- check_availability: Il cliente vuole vedere gli orari disponibili
- book_appointment: Il cliente vuole prenotare uno slot specifico

Estrai questi campi quando presenti:
- service_name: Il servizio desiderato (es. "taglio", "colore", "piega")
- date_reference: Qualsiasi data menzionata (es. "domani", "lunedì prossimo", "15 gennaio")
- time_preference: Preferenza di orario (es. "mattina", "pomeriggio", "verso le 15")
- staff_preference: Preferenza per un operatore specifico
- slot_id: ID dello slot se menzionato
- customer_id: ID cliente se fornito

Rispondi solo con JSON:
{{
  "action": "check_availability" | "book_appointment",
  "confidence": 0.0-1.0,
  "args": {{
    "service_name": "string or null",
    "service_id": "string or null",
    "start_date": "YYYY-MM-DD or null",
    "end_date": "YYYY-MM-DD or null",
    "time_preference": "string or null",
    "staff_id": "string or null",
    "slot_id": "string or null",
    "customer_id": "string or null",
    "notes": "string or null"
  }}
}}

Il cliente ha detto: {user_text}
ID Cliente (se noto): {customer_id}
Data di oggi: {today}

JSON:""",
}


class IntentRouter:
    """
    Routes user utterances to appropriate agents.
    
    Uses LLM to extract structured intent and required parameters
    from natural language user input.
    """

    def __init__(
        self,
        predict_fn: Callable[[str, int], str],
        language: str | None = None,
    ):
        """
        Initialize the intent router.
        
        Args:
            predict_fn: Function to call LLM (prompt, max_tokens) -> response.
            language: Language code ("it"). Defaults to env config.
        """
        self.predict = predict_fn
        config = get_language_config(language)
        self.language = config["code"]
        self._availability_agent = AvailabilityAgent()

    def route(
        self,
        user_text: str,
        customer_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Route user text to an action with extracted arguments.
        
        Args:
            user_text: What the user said.
            customer_id: Optional known customer ID.
        
        Returns:
            Dictionary with action, confidence, and args.
        """
        from datetime import date
        
        prompt_template = ROUTER_PROMPTS["it"]
        prompt = prompt_template.format(
            user_text=user_text,
            customer_id=customer_id or "unknown",
            today=date.today().isoformat(),
        )
        
        response = self.predict(prompt, max_tokens=256)
        
        try:
            result = self._parse_json(response)
        except ValueError:
            result = {
                "action": "check_availability",
                "confidence": 0.2,
                "args": {},
            }
        
        # Post-process: resolve service name to ID
        args = result.get("args", {})
        if args.get("service_name") and not args.get("service_id"):
            service_id = self._availability_agent.resolve_service_id(args["service_name"])
            if service_id:
                args["service_id"] = service_id
        
        # Ensure customer_id is set
        if customer_id and not args.get("customer_id"):
            args["customer_id"] = customer_id
        
        result["args"] = args
        return result

    def get_missing_fields(self, action: str, args: dict[str, Any]) -> list[str]:
        """
        Get list of required fields that are missing.
        
        Args:
            action: The action to check.
            args: Current extracted arguments.
        
        Returns:
            List of missing required field names.
        """
        required_fields = {
            "check_availability": ["service_id", "start_date", "end_date"],
            "book_appointment": ["customer_id", "service_id", "slot_id"],
        }
        
        required = required_fields.get(action, [])
        return [field for field in required if not args.get(field)]

    def _parse_json(self, text: str) -> dict[str, Any]:
        """Parse JSON from LLM response."""
        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the response
        start = text.find("{")
        end = text.rfind("}")
        
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"No JSON found in response: {text[:100]}")
        
        return json.loads(text[start:end + 1])


def create_router(predict_fn: Callable[[str, int], str]) -> IntentRouter:
    """
    Create an intent router with the given prediction function.
    
    Args:
        predict_fn: Function to call LLM.
    
    Returns:
        Configured IntentRouter.
    """
    return IntentRouter(predict_fn)

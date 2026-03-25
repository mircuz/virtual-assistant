"""Intent extraction and guardrail classification via small LLM."""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Awaitable


# Fallback when all parsing fails
_FALLBACK = {"action": "none", "args": {}, "confidence": 0.0, "topic": "booking_related"}

_ACTIONS = [
    "check_availability", "book", "cancel", "reschedule",
    "list_appointments", "ask_service_info", "provide_name",
    "chitchat", "off_topic", "none",
]


class IntentRouter:
    """Routes user text to structured intent via a small/fast LLM."""

    def __init__(
        self,
        predict_fn: Callable[[list[dict], Any], Awaitable[str]],
        services: list[str],
        staff: list[str],
    ):
        self._predict = predict_fn
        self._services = services
        self._staff = staff

    async def route(self, user_text: str) -> dict:
        """Extract intent from user text. Returns dict with action, args, confidence, topic."""
        prompt = self._build_prompt(user_text)
        messages = [{"role": "user", "content": prompt}]

        raw = await self._predict(messages, temperature=0, max_tokens=200)
        result = self._parse_json(raw)
        if result:
            return result

        # Retry with stricter prompt
        retry_prompt = (
            f"Il tuo output precedente non era JSON valido. "
            f"Rispondi SOLO con un oggetto JSON valido per questo messaggio: \"{user_text}\"\n"
            f"Formato: {{\"action\": \"...\", \"args\": {{}}, \"confidence\": 0.0, \"topic\": \"...\"}}"
        )
        raw = await self._predict([{"role": "user", "content": retry_prompt}], temperature=0, max_tokens=200)
        result = self._parse_json(raw)
        return result or _FALLBACK

    def _build_prompt(self, user_text: str) -> str:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        services_str = ", ".join(self._services) if self._services else "nessuno caricato"
        staff_str = ", ".join(self._staff) if self._staff else "nessuno caricato"

        return (
            "Sei un classificatore di intenti per un salone di parrucchieri.\n"
            f"Servizi disponibili: {services_str}\n"
            f"Staff disponibile: {staff_str}\n"
            f"Data e ora corrente: {now}\n\n"
            "Classifica il messaggio del cliente e estrai i parametri.\n"
            f"Azioni possibili: {', '.join(_ACTIONS)}\n"
            "Topic possibili: booking_related, chitchat, off_topic\n\n"
            "Rispondi SOLO con un oggetto JSON valido con questa struttura:\n"
            '{"action": "...", "args": {...}, "confidence": 0.0-1.0, "topic": "..."}\n\n'
            "Per check_availability args deve avere: services (lista nomi), date (YYYY-MM-DD), staff (nome, opzionale)\n"
            "Per book args deve avere: staff_id, service_ids, start_time\n"
            "Per provide_name args deve avere: name\n\n"
            f'Messaggio del cliente: "{user_text}"'
        )

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        """Try to parse JSON from LLM output, handling common issues."""
        text = raw.strip()

        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "action" in data:
                return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the text
        match = re.search(r"\{[^{}]*\}", text)
        if match:
            try:
                data = json.loads(match.group())
                if isinstance(data, dict) and "action" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None

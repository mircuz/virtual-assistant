"""Unified conversation agent: single LLM call for intent + response.

The LLM returns a structured JSON with action + reply, or just plain text.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Callable, Awaitable


class ConversationAgent:
    """Single-call agent: extracts intent + composes response."""

    def __init__(self, predict_fn: Callable[..., Awaitable[str]]):
        self._predict = predict_fn

    async def process(
        self,
        system_prompt: str,
        history: list[dict],
        services: list[str],
        staff: list[str],
    ) -> tuple[str, str, dict]:
        """Process a conversation turn.

        Returns (response_text, action_name, action_args).
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        services_str = ", ".join(services) if services else "nessuno"
        staff_str = ", ".join(staff) if staff else "nessuno"

        enhanced_system = (
            f"{system_prompt}\n\n"
            f"Data e ora corrente: {now}\n"
            f"Servizi disponibili: {services_str}\n"
            f"Staff disponibile: {staff_str}\n\n"
            "ISTRUZIONI:\n"
            "- Rispondi SEMPRE in italiano, in modo naturale e breve (1-2 frasi max)\n"
            "- NON usare mai emoji, simboli o caratteri speciali\n"
            "- Parla come in una telefonata vera: colloquiale, diretto, umano\n"
            "- IMPORTANTE: rispondi SEMPRE con un JSON valido in questo formato:\n"
            '  {"action": "nome_azione", "args": {...}, "reply": "la tua risposta"}\n\n'
            "Azioni disponibili:\n"
            "- provide_name: il cliente dice il suo nome. args: {\"name\": \"...\"}\n"
            "- check_availability: vuole verificare disponibilita. args: {\"services\": [\"...\"], \"date\": \"YYYY-MM-DD\"}\n"
            "- ask_service_info: chiede info sui servizi. args: {}\n"
            "- list_appointments: vuole vedere i suoi appuntamenti. args: {}\n"
            "- goodbye: il cliente saluta/ringrazia e vuole chiudere. args: {}\n"
            "- none: chiacchiere, domande generiche, risposte normali. args: {}\n\n"
            "Rispondi SOLO con il JSON, nient'altro."
        )

        messages = [{"role": "system", "content": enhanced_system}]
        messages.extend(history)

        raw = await self._predict(messages, temperature=0.3, max_tokens=250)
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> tuple[str, str, dict]:
        """Parse LLM output into (response_text, action, args)."""
        text = raw.strip()

        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # Try to parse as JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                reply = data.get("reply", data.get("response", ""))
                action = data.get("action", "none")
                args = data.get("args", {})
                if reply:
                    return (reply, action, args if isinstance(args, dict) else {})
        except json.JSONDecodeError:
            pass

        # Try to find JSON in the text
        match = re.search(r'\{[^{}]*"action"[^{}]*"reply"[^{}]*\}', text, re.DOTALL)
        if not match:
            match = re.search(r'\{[^{}]*"reply"[^{}]*"action"[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return (data.get("reply", ""), data.get("action", "none"), data.get("args", {}))
            except json.JSONDecodeError:
                pass

        # Fallback: treat as plain text response
        return (text, "none", {})

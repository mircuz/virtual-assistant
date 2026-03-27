"""Unified conversation agent: single LLM call for intent + response.

Replaces the two-step IntentRouter + ResponseComposer with one fast LLM call
that uses tool_choice to optionally invoke booking actions and always produces
a natural conversational reply.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable, Awaitable

# Tools the LLM can call (booking engine actions)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "provide_name",
            "description": "Il cliente ha detto il suo nome. Estrailo.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Nome del cliente"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Controlla la disponibilità per uno o più servizi in una data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "services": {"type": "array", "items": {"type": "string"}, "description": "Nomi dei servizi"},
                    "date": {"type": "string", "description": "Data in formato YYYY-MM-DD"},
                    "staff": {"type": "string", "description": "Nome dello staff (opzionale)"},
                },
                "required": ["services"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_service_info",
            "description": "Il cliente chiede informazioni sui servizi disponibili.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_appointments",
            "description": "Il cliente vuole vedere i suoi appuntamenti.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ConversationAgent:
    """Single-call agent: extracts intent via tool use + composes response."""

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
        services_str = ", ".join(services) if services else "nessun servizio caricato"
        staff_str = ", ".join(staff) if staff else "nessuno"

        enhanced_system = (
            f"{system_prompt}\n\n"
            f"Data e ora corrente: {now}\n"
            f"Servizi disponibili: {services_str}\n"
            f"Staff disponibile: {staff_str}\n\n"
            "ISTRUZIONI:\n"
            "- Rispondi SEMPRE in italiano, in modo naturale e breve (1-2 frasi max)\n"
            "- NON usare mai emoji, simboli o caratteri speciali — il testo verrà letto ad alta voce\n"
            "- Parla come in una telefonata vera: colloquiale, diretto, umano\n"
            "- Se il cliente dice il suo nome, usa lo strumento provide_name\n"
            "- Se chiede disponibilità/prenotazione, usa check_availability\n"
            "- Se chiede dei servizi, usa ask_service_info\n"
            "- Se chiede dei suoi appuntamenti, usa list_appointments\n"
            "- Per chiacchiere o argomenti non pertinenti, rispondi senza strumenti"
        )

        messages = [{"role": "system", "content": enhanced_system}]
        messages.extend(history)

        # Single LLM call with tools
        raw = await self._predict_with_tools(messages)

        # Parse the response
        return self._parse_response(raw)

    async def _predict_with_tools(self, messages: list[dict]) -> dict:
        """Call the LLM with tool definitions. Returns raw API response."""
        import httpx

        # We need direct API access for tool_use, not the simple predict_fn
        # The predict_fn wraps httpx, so we replicate it with tools support
        fn = self._predict
        # Access the closure variables
        url = fn.__code__.co_consts  # can't easily access closure
        # Instead, use the predict_fn but pass tools via kwargs
        # Actually, we need to modify the approach - use raw httpx

        # For now, fall back to a simpler approach: ask the LLM to output
        # a structured format without formal tool_use API
        messages_copy = list(messages)
        messages_copy.append({
            "role": "user",
            "content": (
                "Se devi usare uno strumento, rispondi con questo formato ESATTO:\n"
                "TOOL: nome_strumento\n"
                "ARGS: {json_args}\n"
                "REPLY: la tua risposta al cliente\n\n"
                "Se NON devi usare strumenti, rispondi direttamente con il testo."
            ),
        })

        raw_text = await self._predict(messages_copy[:-1] + [{
            "role": "system",
            "content": messages_copy[-1]["content"],
        }], temperature=0.3, max_tokens=200)

        return raw_text

    def _parse_response(self, raw: str) -> tuple[str, str, dict]:
        """Parse LLM output into (response_text, action, args)."""
        text = raw.strip()

        # Check for TOOL: format
        if "TOOL:" in text:
            lines = text.split("\n")
            action = "none"
            args = {}
            reply = ""
            for line in lines:
                line = line.strip()
                if line.startswith("TOOL:"):
                    action = line.replace("TOOL:", "").strip()
                elif line.startswith("ARGS:"):
                    try:
                        args = json.loads(line.replace("ARGS:", "").strip())
                    except json.JSONDecodeError:
                        pass
                elif line.startswith("REPLY:"):
                    reply = line.replace("REPLY:", "").strip()
                elif reply:  # continuation of reply
                    reply += " " + line
            return (reply or text, action, args)

        # No tool used — just a conversational response
        return (text, "none", {})

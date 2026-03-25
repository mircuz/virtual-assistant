"""Natural Italian response generation via large LLM."""
from __future__ import annotations

import json
from typing import Any, Callable, Awaitable

_OFF_TOPIC_RESPONSE = "Mi occupo solo di prenotazioni e servizi per capelli. Posso aiutarti con un appuntamento?"

_NONE_RESPONSE = "Non ho capito bene, puoi ripetere?"


class ResponseComposer:
    """Generates natural Italian conversational responses."""

    def __init__(self, predict_fn: Callable[[list[dict], Any], Awaitable[str]]):
        self._predict = predict_fn

    async def compose(
        self,
        system_prompt: str,
        history: list[dict],
        action: str,
        action_result: dict | None,
    ) -> str:
        # Static responses for guardrails
        if action == "off_topic":
            return _OFF_TOPIC_RESPONSE
        if action == "none":
            return _NONE_RESPONSE

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)

        # Add context about what happened
        if action_result is not None:
            context = (
                f"[Risultato azione '{action}': {json.dumps(action_result, default=str, ensure_ascii=False)}]\n"
                "Rispondi al cliente in modo naturale, massimo 1-2 frasi."
            )
        else:
            context = (
                f"[Azione: {action}. Nessun dato aggiuntivo.]\n"
                "Rispondi al cliente in modo naturale, massimo 1-2 frasi."
            )

        messages.append({"role": "system", "content": context})

        return await self._predict(messages, temperature=0.7, max_tokens=150)

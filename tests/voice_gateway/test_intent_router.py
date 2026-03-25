import pytest
import json
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_parse_valid_json():
    from voice_gateway.conversation.intent_router import IntentRouter

    async def mock_predict(messages, **kwargs):
        return '{"action": "check_availability", "args": {"services": ["taglio"], "staff": "Mirco"}, "confidence": 0.95, "topic": "booking_related"}'

    router = IntentRouter(predict_fn=mock_predict, services=["Taglio donna"], staff=["Mirco Meazzo"])
    result = await router.route("Vorrei un taglio con Mirco domani")
    assert result["action"] == "check_availability"
    assert result["topic"] == "booking_related"


@pytest.mark.asyncio
async def test_parse_json_with_markdown_fences():
    from voice_gateway.conversation.intent_router import IntentRouter

    async def mock_predict(messages, **kwargs):
        return '```json\n{"action": "chitchat", "args": {}, "confidence": 0.8, "topic": "chitchat"}\n```'

    router = IntentRouter(predict_fn=mock_predict, services=[], staff=[])
    result = await router.route("Ciao, come stai?")
    assert result["action"] == "chitchat"
    assert result["topic"] == "chitchat"


@pytest.mark.asyncio
async def test_fallback_on_garbage():
    from voice_gateway.conversation.intent_router import IntentRouter

    call_count = 0
    async def mock_predict(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        return "this is not json at all"

    router = IntentRouter(predict_fn=mock_predict, services=[], staff=[])
    result = await router.route("something weird")
    assert result["action"] == "none"
    assert result["topic"] == "booking_related"
    assert call_count == 2  # original + retry


@pytest.mark.asyncio
async def test_off_topic_classification():
    from voice_gateway.conversation.intent_router import IntentRouter

    async def mock_predict(messages, **kwargs):
        return '{"action": "off_topic", "args": {}, "confidence": 0.99, "topic": "off_topic"}'

    router = IntentRouter(predict_fn=mock_predict, services=[], staff=[])
    result = await router.route("Cosa ne pensi delle elezioni?")
    assert result["topic"] == "off_topic"

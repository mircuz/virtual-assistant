import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_compose_booking_response():
    from voice_gateway.conversation.response_composer import ResponseComposer

    async def mock_predict(messages, **kwargs):
        return "Mirco è disponibile domani alle 14 o alle 16:30. Quale preferisci?"

    composer = ResponseComposer(predict_fn=mock_predict)
    result = await composer.compose(
        system_prompt="Sei l'assistente di Salon Bella.",
        history=[{"role": "user", "content": "Vorrei un taglio con Mirco domani"}],
        action="check_availability",
        action_result={"slots": [{"staff_name": "Mirco", "slot_start": "2026-03-30T14:00", "slot_end": "2026-03-30T14:45"}]},
    )
    assert "Mirco" in result


@pytest.mark.asyncio
async def test_compose_chitchat_response():
    from voice_gateway.conversation.response_composer import ResponseComposer

    async def mock_predict(messages, **kwargs):
        return "Bene grazie! Come posso aiutarti oggi?"

    composer = ResponseComposer(predict_fn=mock_predict)
    result = await composer.compose(
        system_prompt="Sei l'assistente.",
        history=[{"role": "user", "content": "Ciao come stai?"}],
        action="chitchat",
        action_result=None,
    )
    assert "grazie" in result.lower()


@pytest.mark.asyncio
async def test_compose_off_topic_static():
    from voice_gateway.conversation.response_composer import ResponseComposer

    composer = ResponseComposer(predict_fn=AsyncMock())
    result = await composer.compose(
        system_prompt="", history=[], action="off_topic", action_result=None,
    )
    assert "prenotazioni" in result.lower() or "capelli" in result.lower()

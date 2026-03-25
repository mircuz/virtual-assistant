from voice_gateway.conversation.prompt_assembler import assemble_system_prompt


def test_assembles_full_prompt():
    config = {
        "name": "Salon Bella",
        "personality": "Sei Bella, solare e cordiale.",
        "tone_instructions": "Amichevole, dai del tu",
        "special_instructions": "Suggerisci servizi simili",
    }
    prompt = assemble_system_prompt(config)
    assert "Salon Bella" in prompt
    assert "Sei Bella" in prompt
    assert "Amichevole" in prompt
    assert "Suggerisci servizi simili" in prompt
    assert "italiano" in prompt.lower()


def test_handles_missing_fields():
    config = {"name": "Test Shop"}
    prompt = assemble_system_prompt(config)
    assert "Test Shop" in prompt
    assert "italiano" in prompt.lower()

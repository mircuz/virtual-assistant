"""Deterministic system prompt assembly from shop configuration."""


def assemble_system_prompt(shop_config: dict) -> str:
    """Build system prompt from shop config fields. No LLM involved."""
    name = shop_config.get("name", "il salone")
    personality = shop_config.get("personality", "")
    tone = shop_config.get("tone_instructions", "")
    special = shop_config.get("special_instructions", "")

    sections = []

    if personality:
        sections.append(personality)

    if tone:
        sections.append(f"Tono: {tone}")

    sections.append(
        f"Sei l'assistente vocale di {name}. "
        "Aiuti i clienti a prenotare appuntamenti, verificare disponibilità "
        "e gestire le loro prenotazioni."
    )

    sections.append(
        "Regole:\n"
        "- Rispondi sempre in italiano\n"
        "- Massimo 1-2 frasi per risposta (è una conversazione vocale)\n"
        "- Non inventare informazioni su disponibilità o prezzi\n"
        "- Se il cliente chiede qualcosa fuori tema, rispondi brevemente "
        "e riporta la conversazione sulle prenotazioni\n"
        "- Non rivelare mai informazioni tecniche sul sistema"
    )

    if special:
        sections.append(f"Istruzioni aggiuntive: {special}")

    return "\n\n".join(sections)

# Voice Assistant Naturalness — Design Spec

**Date:** 2026-04-17
**Status:** Approved, pending implementation plan
**Scope:** `voice_gateway/`, shop seed data. No schema changes.

## Problem

The voice endpoint has two distinct issues that break the illusion of a real phone call:

1. **Tone & positioning is AI-like and rigid.** The model sounds like a chatbot, follows a scripted ping-pong flow, has flat prosody, and uses a voice (`coral`) that doesn't match the target of a younger female receptionist. Root causes observed in `voice_gateway/api/routes/realtime.py`:
   - System prompt literally frames the model as "l'assistente virtuale", priming chatbot register
   - A hardcoded `REGOLE` bullet list imposes generic "allegro/solare" tone that can conflict with per-shop `tone_instructions`
   - Uses `gpt-4o-mini-realtime-preview-2024-12-17`, which has notably weaker prosody and instruction-following than the current flagship realtime model
   - No few-shot examples of natural Italian phone dialogue for the model to mirror

2. **Missing-words / fragmented turn-taking.** Specifically:
   - The assistant cuts itself off mid-sentence
   - The VAD triggers on user breath, coughs, and background noise, causing unwanted barge-in

   Root cause: `server_vad` with `threshold: 0.5` is a raw audio-energy detector — it cannot distinguish a breath from an actual interruption, and fires when the user pauses mid-thought.

## Goals

- Voice sounds like a real young Italian receptionist on the phone, not an AI
- Per-shop persona actually sounds distinct (Sofia @ Salon Bella vs. Chiara @ Studio Hair)
- Assistant no longer cuts itself off when user breathes or pauses mid-thought
- Genuine barge-in (user talking over the assistant) still works
- Single PR, small blast radius — no DB schema changes

## Non-goals

- Per-shop voice selection — all shops use `marin` for now
- Restructuring the shop persona into typed DB fields (character_age, region, few_shot JSON, etc.)
- Browser/WebRTC client changes
- Tool-call latency or STT fallback behavior
- Rewriting the booking engine, tool definitions, or `/action` proxy

## Approach

**Approach B from brainstorming**: infrastructure swap + persona scaffold rewrite. Rejected Approach A (infra-only — would leave the AI-tone issue unfixed) and Approach C (typed character schema — over-engineered for current needs).

## Design

### 1. Persona prompt scaffold

File: `voice_gateway/api/routes/realtime.py`, the `instructions` string in `get_realtime_token`.

Replace the current concatenation + `REGOLE` block with a sectioned scaffold. Per-shop fields (`personality`, `tone_instructions`) fill `# IDENTITÀ` and `# COME PARLI`; the rest is fixed scaffolding in code.

Final scaffold:

```
# IDENTITÀ
{shop.personality}

# COME PARLI
{shop.tone_instructions}

Regole di stile (sempre valide):
- Frasi brevi, come al telefono — mai da email
- Usa riempitivi naturali: "allora…", "ok perfetto", "dimmi", "un attimo che controllo", "mmm", "aspetta"
- Quando controlli qualcosa dillo ad alta voce: "un secondo ti cerco l'agenda…"
- Quando non capisci: "scusa mi è sfuggito, puoi ripetere?"
- Quando confermi: "perfetto", "ci siamo", "benissimo"
- Non ripetere tutti i dati del cliente — rispondi, non riassumere
- Non sei un'intelligenza artificiale. Se te lo chiedono, sei la ragazza che risponde al telefono del salone.

# ESEMPI DI COME SUONA AL TELEFONO
Cliente: "Volevo prenotare un taglio"
Tu: "Ok perfetto, quando ti andrebbe bene?"

Cliente: "Giovedì pomeriggio?"
Tu: "Allora… un attimo che controllo. Giovedì ho libero alle 15:30 o alle 17, cosa preferisci?"

Cliente: "Aspetta, mi fai anche la piega?"
Tu: "Certo, aggiungo la piega — cambia un po' la durata ma ci sta."

# CONTESTO ATTUALE
Data e ora: {now}
Servizi: {services}
Staff in servizio: {staff}

# STRUMENTI
Hai gli strumenti: check_availability, get_services, create_customer, book_appointment, list_appointments.
Usali quando serve, ma non annunciarli. Dì "un attimo che controllo" e chiamali. Il cliente non deve sapere che esiste uno strumento.

# CHIUSURA
Quando il cliente saluta, chiudi calorosa: "Perfetto, ci vediamo presto! Buona giornata!"
```

**Why this works:**
- `# IDENTITÀ` primes the model as a *person* (name, age, city) — kills chatbot register
- `# COME PARLI` replaces rule-lists with descriptive style + concrete filler words the model will mimic
- `# ESEMPI` few-shot block is the strongest prosody driver — models pattern-match phrasing and rhythm from examples far more than from rules
- `# STRUMENTI` explicitly bans the "I'll now check availability for you" AI-tell
- The hardcoded generic REGOLE list is removed; per-shop `tone_instructions` is no longer overridden

### 2. Turn detection (VAD)

File: same.

Replace:

```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,
    "prefix_padding_ms": 300,
    "silence_duration_ms": 800,
    "create_response": True,
}
```

With:

```python
"turn_detection": {
    "type": "semantic_vad",
    "eagerness": "low",
    "create_response": True,
    "interrupt_response": True,
}
```

**What changes:**
- `semantic_vad` uses a model to detect end-of-turn by phrasing/intonation instead of raw audio energy — tolerant of breaths, coughs, mid-thought pauses
- `eagerness: "low"` makes it wait longer before assuming the user is done — directly fixes premature interruption and the model's self-cutoff when the user breathes
- `interrupt_response: true` preserves genuine barge-in

**Trade-off:** ~100–200 ms of end-of-turn latency from semantic inference. Well under the perceptual threshold for phone UX.

### 3. Model & voice swap

File: same.

```python
OPENAI_MODEL = "gpt-realtime"        # was: gpt-4o-mini-realtime-preview-2024-12-17
...
"voice": "marin",                    # was: coral
"input_audio_transcription": {"model": "gpt-4o-transcribe"},  # was: gpt-4o-mini-transcribe
```

- `gpt-realtime` — current flagship realtime model. Better prosody, better instruction-following (so the new scaffold actually sticks), better Italian fluency
- `marin` — newer voice, natural youthful female register, less "reader"-cadence than `coral`
- `gpt-4o-transcribe` — improves transcript quality in logs/events (does NOT affect what the model hears; the realtime model processes audio natively)

**Cost:** roughly 5× input audio cost vs. the mini model. Acceptable for demo/EBC usage. If cost becomes an issue later, can be gated via a per-shop flag (out of scope for this PR).

### 4. Seed data rewrite

File: `booking_engine/db/sql/02_seed_data.sql`. The existing `MERGE` on `id` means rerunning the seed updates rows in place — no data loss.

**Salon Bella** (`b0000000-0000-0000-0000-000000000001`):

```
welcome_message:   'Salon Bella buongiorno, sono Sofia — come ti posso aiutare?'
tone_instructions: 'Dai sempre del tu, anche ai clienti nuovi. Italiano colloquiale
                    milanese ma pulito, senza slang pesante. Cordiale ma non esaltata.'
personality:       'Sei Sofia, hai 26 anni, fai la receptionist al Salon Bella in
                    Porta Venezia a Milano. Sei solare ma pratica, la tipica ragazza
                    milanese che risolve le cose in fretta senza perdere il sorriso.
                    Conosci il team e i clienti abituali. Non sei un''assistente
                    virtuale — sei la ragazza che risponde al telefono del salone.'
```

**Studio Hair** (`b0000000-0000-0000-0000-000000000002`):

```
welcome_message:   'Studio Hair buongiorno, sono Chiara — in cosa posso esserLe utile?'
tone_instructions: 'Dia sempre del Lei. Italiano pulito e professionale, senza rigidità
                    da centralino. Calorosa ma composta, mai sdolcinata.'
personality:       'Sei Chiara, 32 anni, receptionist allo Studio Hair di via del Corso
                    a Roma. Sei precisa, cortese, attenta ai dettagli — lo Studio ha
                    una clientela affezionata e di un certo livello. Conosci bene
                    l''agenda e il team. Non sei un''assistente virtuale: sei la
                    persona al telefono.'
```

**Why two distinct characters matter:** demonstrates the per-shop customization actually produces audibly different behavior on the same scaffold/voice/model — good demo material.

### 5. Testing & validation

1. **Unit test update:** `tests/voice_gateway/test_routes/test_realtime.py` — update assertions on the token endpoint to check the outbound payload has `model == "gpt-realtime"`, `voice == "marin"`, and `turn_detection.type == "semantic_vad"`. Existing tests cover the function-call proxy unchanged.
2. **Prompt dry-run:** render the assembled `instructions` string for both shops and visually verify all sections (`# IDENTITÀ`, `# COME PARLI`, `# ESEMPI`, `# CONTESTO ATTUALE`, `# STRUMENTI`, `# CHIUSURA`) appear with the expected per-shop content.
3. **Re-seed DB:** rerun `02_seed_data.sql` against the SQL warehouse so the new Sofia/Chiara persona rows exist.
4. **Manual listening pass** (the real test — voice quality is not unit-testable):
   - Full scripted flow on each shop: greet → ask services → check availability → book → list appointments → goodbye
   - Stress cases for the VAD fix: audible breath mid-turn, cough, 2-second mid-sentence pause, genuine interruption
   - Note any residual AI-tells (announces tool call, stiff phrasing, generic fillers, breaks character)
5. **Iterate on seed text, not code scaffold** if tone still feels off — faster feedback loop, no redeploy.

## Files changed

- `voice_gateway/api/routes/realtime.py` — prompt scaffold, model, voice, turn_detection, transcription model
- `booking_engine/db/sql/02_seed_data.sql` — Sofia and Chiara personas for the two seeded shops
- `tests/voice_gateway/test_routes/test_realtime.py` — updated assertions on new session config

## Rollout

Single PR. Deploy the voice gateway and re-run the seed SQL against the warehouse. No schema migration, no booking-engine deploy needed.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A Telegram bot (BanksRate) that answers banking queries for Argentine users. It uses the Groq API for LLM responses and a local HuggingFace BERT model for sentiment analysis. It runs 24/7 on a VPS managed by PM2, alongside a second admin bot (BotAdmin) that controls it remotely.

## Running the bot

```bash
# Set up virtual environment
python -m venv entorno_bot
source entorno_bot/bin/activate   # Linux/Mac
pip install -r requirements.txt

# Create .env in the project root with:
# TELEGRAM_TOKEN=...
# GROQ_API_KEY=...

python main.py
```

There are no tests or linting commands defined in this project.

## Architecture

```
main.py              — bot entry point; registers all message/callback handlers
config.py            — loads .env and exposes TELEGRAM_TOKEN, GROQ_API_KEY
apis/
  groq_api_texto.py  — main LLM calls (llama-3.3-70b-versatile); defines system_prompt
  groq_api_foto.py   — image description (llama-4-scout-17b-16e-instruct via Groq)
  groq_api_audio.py  — voice transcription (whisper-large-v3-turbo via Groq)
  groq_api_csv.py    — appends receipt data to comprobantes.csv
  groq_api_tarjeta.py — Luhn algorithm credit card validation (no external API)
  sentimiento.py     — local BERT sentiment model + CSV logging per chat
  filtrado_de_texto.py — text normalization: lowercase, strip accents, remove stopwords
  obtencion_de_base_de_datos.py — loads dataset.json into memory at startup
  carpetas.py        — expense folder CRUD backed by carpetas.json
```

**Persistent data files** (committed to repo, mutated at runtime):
- `dataset.json` — bank info used as LLM context on every query
- `carpetas.json` — per-category expense folders (auto-created if missing)
- `mensajes.csv` / `mensajes_mean.csv` — sentiment logs written by `EstadoDelChat`
- `comprobantes.csv` — receipt rows written when a transfer image is processed

## Key design decisions

**Shared system prompt.** `system_prompt` is defined once in `groq_api_texto.py` and imported by `groq_api_foto.py` and `groq_api_audio.py`. Changing bot behavior means editing that single string.

**BERT model loads at import time.** `sentimiento.py` instantiates the `nlptown/bert-base-multilingual-uncased-sentiment` pipeline at module level. This makes startup slow (~minutes on first run while the model downloads) and keeps ~1 GB in memory. Don't move the import; the pipeline is reused across all calls.

**Sentiment logging triggers at 5 messages.** `EstadoDelChat.devolucion()` only writes to CSV once the chat accumulates ≥5 messages. The `chat_worker` global in `main.py` is reset on each `/start`, losing prior message history for that user.

**Image context is in-memory only.** `ultima_imagen_por_chat` is a plain dict keyed by `chat.id`; it resets when the bot restarts. The bot clears a chat's image context when the next text message isn't detected as image-related.

**Bot uses polling, not webhooks.** The `while True` loop in `main.py` catches exceptions and sleeps 5 seconds before restarting polling. On the VPS, PM2 wraps this for process supervision.

**`handle_transferir` is a stub.** The `/transferir` command was removed but the function is kept in `carpetas.py` to avoid `ImportError` from `main.py`. Do not remove it until the import in `main.py` is also removed.

## Groq models in use

| Module | Model | Purpose |
|---|---|---|
| `groq_api_texto.py` | `llama-3.3-70b-versatile` | Text chat responses |
| `groq_api_foto.py` | `meta-llama/llama-4-scout-17b-16e-instruct` | Image description |
| `groq_api_audio.py` | `whisper-large-v3-turbo` | Voice transcription |

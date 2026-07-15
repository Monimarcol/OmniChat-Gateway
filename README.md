# OmniChat Gateway

A local-first AI chat assistant. On first run, it detects your hardware, asks what you'll use it for, and uses an LLM agent to recommend and set up the right local model for your device and use case -- no manual model selection, no terminal commands, no data leaving your machine.

Runs entirely on [Ollama](https://ollama.com/) locally. No cloud API keys, no account, no telemetry.

## Quickstart (Windows)

Double-click **`start.bat`** (or run it from a terminal). First run will:

1. Install Ollama if it isn't already present.
2. Pull the default model (`llama3`).
3. Write `.env` with sane defaults.
4. Set up a Python virtual environment and install dependencies.
5. Start the backend and open the chat UI in your browser.

Subsequent runs skip whatever's already done and go straight to launching the app.

## How it works

```
Hardware detection -> describe your use case -> model recommendation -> chat
```

1. **Hardware detection** (`app/hardware.py`): a one-shot scan of CPU, RAM, and GPU, cached for 24h. No background polling.
2. **Use case description**: plain-language text, e.g. "drafting blog posts and brainstorming article ideas."
3. **Model recommendation** (`app/recommender.py`): a deterministic filter first narrows the model catalog to what actually fits the device's available RAM, then an LLM agent (running on the already-guaranteed-present `llama3`) ranks the feasible models against the stated use case and explains why, in plain language. The agent can only affect ranking and rationale -- it can never recommend a model that won't run on the device.
4. **Model setup**: picking a recommended (or manually chosen) model triggers an on-demand `ollama pull` if it isn't already local.
5. **Chat**: the Streamlit UI sends each message to the FastAPI backend with the selected model, which calls Ollama via `litellm` and returns the response. History is stored in SQLite, grouped by conversation.

## Manual setup

```
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\uvicorn.exe app.main:app --reload
.venv\Scripts\streamlit.exe run chat_ui.py
```

Requires Python 3.12 specifically for some dependencies (see `requirements.txt` comments / release notes) -- prebuilt wheels for the newest CPython often lag behind.

## API

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness check |
| `GET /hardware` | Detected CPU/RAM/GPU profile |
| `GET /models` | Full model catalog |
| `POST /models/recommend` | `{"description": "..."}` -> ranked, explained model shortlist |
| `POST /models/{id}/ensure` | Pulls the model via Ollama if not already local |
| `POST /chat` | `{"model": "ollama/...", "conversation_id": "...", "messages": [...]}` |
| `GET /history/{conversation_id}` | Message history for a conversation |

## Configuration

Set via `.env` (written automatically by `setup.ps1`):

| Variable | Default |
|---|---|
| `MODEL_NAME` | `ollama/llama3` -- fallback used when a chat request doesn't specify a model |
| `API_BASE` | `http://127.0.0.1:11434` -- Ollama's local API |
| `DATABASE_URL` | `sqlite:///./chat_history.db` |

## Project history

This project absorbed the hardware-detection and model-recommendation work originally prototyped separately under the name "Kade-AI." That work is now maintained here going forward. See [RELEASE_NOTES.md](RELEASE_NOTES.md) for the detailed changelog.

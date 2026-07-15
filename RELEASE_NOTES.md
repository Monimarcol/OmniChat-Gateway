# Release notes

All notable changes to this project are documented here. Dates reflect when the change was merged.

## Unreleased

### Added
- Hardware-aware setup flow: on first use, the app detects CPU/RAM/GPU and walks the user through describing their use case before picking a model. This replaces Kade-AI as a separate project -- that work is now merged directly into this repo, which is the project going forward.
- Model recommendation agent (`app/recommender.py`): an LLM call (using the default `llama3` model) reasons about which locally-runnable model best fits the user's stated use case, with a plain-language rationale per suggestion. A deterministic hardware-fit filter runs first, so the agent can only affect ranking/rationale among models that are already confirmed to fit the device -- it can never recommend something that won't run.
- On-demand model pulling: selecting a non-default model in the setup flow pulls it via Ollama automatically (`POST /models/{id}/ensure`), no manual `ollama pull` required.
- New backend endpoints: `GET /health`, `GET /hardware`, `GET /models`, `POST /models/recommend`, `POST /models/{id}/ensure`.
- The backend now honors a per-request `model` field on `/chat` instead of always using the `.env` default, so a chat session actually uses whatever model the user selected during setup.
- `RELEASE_NOTES.md` (this file) and a proper `README.md`.

### Fixed
- `requirements.txt` was missing `streamlit` and `requests`, both imported directly by `chat_ui.py` -- a plain `pip install -r requirements.txt` did not produce a working app.
- `litellm`'s latest release ships no prebuilt Windows wheel and pulls in a Rust build that fails without a preconfigured toolchain; pinned to `1.91.3`, which ships a wheel.
- `API_BASE` defaulted to `http://localhost`, which can resolve to IPv6 first and fail to reach Ollama's IPv4-only loopback binding on some machines; switched to `127.0.0.1` throughout.
- `database.py` hardcoded its own `DATABASE_URL`, silently ignoring the value from `.env`/`config.py`. Now reads from `settings.DATABASE_URL`.
- Removed `app/router.py`, dead code that duplicated `services.py` and was never imported.

## v1.1.0 -- one-click setup

- Added `start.bat` / `setup.ps1`: installs Ollama, pulls the default `llama3` model, provisions a Python virtual environment, writes `.env`, and launches the FastAPI backend and Streamlit chat UI in one step. No terminal commands required from the user.
- Added `GET /health` so the setup script can detect when the backend is actually ready.

## v1.0.0 -- initial architecture

- FastAPI backend (`app/main.py`) calling a local Ollama model via `litellm`.
- SQLite-backed chat history (`app/database.py`), grouped by `conversation_id`.
- Streamlit chat UI (`chat_ui.py`) talking to the backend over HTTP.
- `.env`-based configuration for model name, Ollama API base, and database URL.

# Email Labeler — Comprehensive README

> **What it does (short):**
> A small FastAPI + Streamlit project that fetches your Gmail, runs an AI agent to generate a single label per email, creates labels in Gmail (if needed), and applies them — all via a backend API and a Streamlit front-end.

This README replaces and expands the brief README included in the repository. It documents architecture, setup, configuration, endpoints, developer notes, and troubleshooting so you can run, modify, and extend the project.

---

## Table of contents

1. [Highlights / Features](#highlights--features)
2. [Architecture & key files](#architecture--key-files)
3. [Prerequisites](#prerequisites)
4. [Setup & configuration (settings.py)](#setup--configuration-settingspy)
5. [Install & run locally](#install--run-locally)
6. [Docker](#docker)
7. [API endpoints (summary & examples)](#api-endpoints-summary--examples)
8. [How the AI agent decides labels](#how-the-ai-agent-decides-labels)
9. [Security & secrets handling](#security--secrets-handling)
10. [Limitations & cautions](#limitations--cautions)
11. [Troubleshooting & tips](#troubleshooting--tips)
12. [Development notes & extending the project](#development-notes--extending-the-project)
13. [Contributing & license](#contributing--license)

---

## Highlights / Features

* FastAPI backend that performs Google OAuth2 and proxies Gmail interactions.
* Streamlit UI to initiate sign-in, fetch messages, and run automatic labeling.
* Simple AI agent (uses `ollama.chat`) which returns **exactly one** label per email.
* Creates Gmail labels when needed and applies them.
* JWT-based API token flow between frontend and API.

---

## Architecture & key files

```
email-labeler-master/
├─ api/                       # FastAPI app
│  ├─ app.py                  # Main FastAPI app + endpoints
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ utils/                  # helpers for OAuth & secrets for API
│     ├─ auth.py
│     ├─ jwt.py
│     └─ credentials_manager.py
├─ email_agent/               # AI agent wrapper and prompts
│  ├─ agent.py                # Agent class using ollama.chat
│  ├─ system_prompt.py        # System prompt (rules for labelling)
│  └─ util.py                 # constructs the user prompt
├─ main.py                    # Streamlit front-end
├─ utils/__init__.py          # GmailClient, encode_tok (used by Streamlit)
├─ requirements.txt           # top-level requirements (streamlit etc)
├─ README.md (old)            # replaced with this file
└─ test.py
```

**Quick notes about responsibilities**

* `api/app.py` — handles google OAuth flow, creates/returns an API token (JWT), and exposes endpoints used by the UI (`/emails`, `/labels`, `/emails/{id}/label`, etc).
* `main.py` — Streamlit UI: calls API endpoints, obtains token, displays logs & status, orchestrates labeling of fetched messages.
* `email_agent/` — encapsulates label generation logic. The agent calls the local Ollama model via `ollama.chat` (so you need an Ollama runtime or change to another LLM provider).

---

## Prerequisites

* Python 3.11 (the Dockerfile uses 3.11; local venv recommended)
* Google Cloud project with OAuth 2.0 Client ID for a web application (to use Gmail API scopes).
* Gmail API enabled for your Google project.
* `ollama` local server OR change agent to another model provider (agent currently calls `ollama.chat`).

  * If you don't have Ollama, either install and run Ollama locally or modify `email_agent/agent.py` to call OpenAI/Hugging Face/other LLM APIs.
* System packages for building some Python packages (if using Docker, the `Dockerfile` installs `build-essential`).
* (Optional) Docker and Docker Compose to containerize.

---

## Setup & configuration (`settings.py`)

This repo expects a `settings` module that exposes a `secrets` mapping. The repo does **not** include your secrets. Create a `settings.py` in the repository root with a structure like this:

```python
# settings.py (example)
secrets = {
    "google_secrets": {
        "client_id": "YOUR_GOOGLE_CLIENT_ID",
        "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
        # The redirect URI set in Google Cloud console, e.g.
        # "http://localhost:8000/auth/callback"
        "client_redirect_uri": "http://localhost:8000/auth/callback",
    },
    "jwt_secrets_api": {
        # used by FastAPI app jwt manager
        "jwt_secret": "super-secret-for-api-jwt-signing",
        "jwt_decode_secret": "super-secret-for-decode",
        "jwt_algorithm": "HS256",
        # optional expiry seconds (default used if omitted)
        "jwt_expiry_seconds": 3600
    },
    "web_secrets": {
        # used by Streamlit client for its encode_tok function
        "jwt_secret": "different-or-same-secret-used-for-web-encoding"
    }
}
```

**Important:** Keep `settings.py` out of version control (add to `.gitignore`). Use environment variables or a secret manager for production.

---

## Install & run locally

1. Create & activate venv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r api/requirements.txt
```

2. Create `settings.py` (see above) and ensure your Google credentials & redirect URI match your Google Cloud OAuth client.

3. Start the FastAPI API:

```bash
# from repository root
uvicorn api.app:app --reload --port 8000
```

4. Start the Streamlit UI:

```bash
streamlit run main.py
```

5. Open Streamlit in browser (usually `http://localhost:8501`) and follow the login flow.

---

## Docker

A simple `api/Dockerfile` exists for the backend. Example build + run:

```bash
# build
docker build -t email-labeler-api -f api/Dockerfile .

# run (make sure you provide settings / secrets to the container)
docker run -p 8000:8000 \
  -e SOME_ENV_VAR=... \
  email-labeler-api uvicorn api.app:app --host 0.0.0.0 --port 8000
```

You will need to mount or provide the `settings.py` contents or environment variables into the container. The Dockerfile builds a slim Python image but does not configure secrets for you.

---

## API endpoints (summary & examples)

The FastAPI app exposes these endpoints (as present in `api/app.py`):

* `GET /`

  * Basic ping/close tab helper used by the OAuth flow.

* `GET /auth/login`

  * Returns/redirects to Google OAuth URL for user sign-in.

* `GET /auth/callback?code=...`

  * OAuth2 callback endpoint. Exchanges the authorization code for Google credentials and creates an internal JWT token to be consumed by the frontend.

* `GET /token`

  * Waits for the internal JWT to be ready (created when user completes OAuth). The Streamlit client polls this to retrieve the signed API token.

* `GET /labels`

  * Returns existing labels (pulled via Gmail API) — requires API token.

* `POST /labels?new_label_name=...`

  * Creates a new Gmail label with the provided name. Returns created `labelId`.

* `GET /emails`

  * Fetches a batch of emails from Gmail (the implementation uses chunking and respects some query params). Requires API token.

* `POST /emails/{msg_id}/label?label_id=...`

  * Applies a label (by id) to a message id.

### Example: apply a label via curl

```bash
curl -X POST "http://localhost:8000/emails/12345/label?label_id=LABEL_ABC" \
  -H "Authorization: Bearer <api-jwt-token>"
```

> Note: The code uses an OAuth2 token flow and `OAuth2PasswordBearer` security dependency. The Streamlit front-end exchanges the signed token and then calls these endpoints with `Authorization: Bearer <token>`.

---

## How the AI agent decides labels

The AI agent code lives in `email_agent/`. Key behavior:

* `SystemPrompts.EMAIL_AGENT` defines strict rules:

  * Return **exactly one label**, **only the label** (no explanation).
  * Prefer organization names from subject or the sender domain.
  * Keep label to at most three words.
  * Always output only the label string.

* `Agent.generate_label(email_data, existing_labels)`

  * Builds a prompt from `email_data` (subject, from, date, snippet, attachments) using `email_agent/util.py`.
  * Calls `ollama.chat` with a model (default `"llama3.2:1b"`) and returned content is used as the label.
  * Response is appended to conversation history (so the agent preserves continuity).

**If you want to replace Ollama**: modify `email_agent/agent.py` to call OpenAI or another model provider and adapt message format accordingly.

---

## Security & secrets handling

* **Do not commit** `settings.py` or your client secret to git.
* JWT flows:

  * The API creates/signs a JWT token after successful Google OAuth exchange.
  * The client (Streamlit) polls `/token` to obtain the API token and then uses it to call protected endpoints.
* Use HTTPS for production deployments.
* Limit the OAuth redirect URIs to only allowed domains in Google Cloud Console.
* Consider rotating JWT secrets and using a vault for secrets in production (AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager).

---

## Limitations & cautions

* **Ollama required**: `email_agent` calls `ollama.chat`. If Ollama server is not running or not installed, the agent will fail. You can replace this with OpenAI calls if you prefer.
* **Gmail quotas & rate limits**: Be mindful of Gmail API quotas if you fetch/apply labels across many messages.
* **Label collisions**: The agent returns label strings; the repo creates labels if they don't exist. Names are used as-is — consider normalization (case, punctuation) in a future enhancement.
* **No production authentication hardening**: The JWT scheme in the samples is simple. In production you should validate tokens robustly and consider refresh tokens, revocation, rate limiting, CORS rules, and proper origin checks.
* **No database**: This is an API + UI. There's no persistence beyond what Gmail holds — e.g., label mappings are kept in-memory inside the Streamlit session. For scale, add a DB.

---

## Troubleshooting & tips

* **OAuth redirect mismatch**: Ensure the `client_redirect_uri` in `settings.py` exactly matches the redirect URI registered in Google Cloud console.
* **Token not available / polling `/token`**: The UI polls `/token` until the API has created a JWT for the session. Check `api` logs for OAuth callback errors if polling times out.
* **Ollama errors**: If you see errors from `ollama.chat`, confirm Ollama is installed and running, or modify `agent.py` to target a different provider.
* **Permissions**: Ensure the OAuth scope includes `https://www.googleapis.com/auth/gmail.modify` for labeling messages.
* **Local testing**: Use `ngrok` if you need public URL for Google OAuth callback during local dev.
* **Running large volumes of email**: The Streamlit UI processes a chunk at a time. For very large mailboxes (thousands), batch and add retries/backoff. Avoid doing everything in the browser in one go.

---

## Development notes & extending the project

**Where to change labeling rules**

* `email_agent/system_prompt.py` — edit the system prompt rules the LLM follows.
* `email_agent/util.py` — change the information you pass to the model (for instance, include more snippet text, thread context, or extracted entities).

**To swap LLM provider**

* Modify `email_agent/agent.py`:

  * Replace `ollama.chat(...)` with an OpenAI call or your LLM client.
  * Keep the message format and system prompt semantics consistent (system/user/assistant roles) or adapt prompt engineering accordingly.

**Add a persistence layer**

* Add a DB to store processed message IDs, label mappings, and audit logs (so re-processing is idempotent).

**Unit tests**

* Add tests for prompt generation, label normalization logic, and API endpoints (use FastAPI TestClient).

---

## Example `settings.py` (full example)

```python
# settings.py
secrets = {
    "google_secrets": {
        "client_id": "YOUR_GOOGLE_CLIENT_ID",
        "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
        "client_redirect_uri": "http://localhost:8000/auth/callback"
    },
    "jwt_secrets_api": {
        "jwt_secret": "replace-with-a-secure-secret",
        "jwt_decode_secret": "replace-with-a-secure-decode-secret",
        "jwt_algorithm": "HS256",
        "jwt_expiry_seconds": 3600
    },
    "web_secrets": {
        "jwt_secret": "replace-with-web-jwt-secret"
    }
}
```

---

## Contributing

* Fork + PR. Keep secrets out of commits.
* Add unit tests for core logic (`email_agent/util.py`, `api/app.py` endpoints).
* If you change LLM provider, add a configuration switch to pick provider by env var.

---

## License

(Repository had none included). Add a license file before publishing. Suggested: MIT for permissive use.

---

## Final notes (TL;DR)

* Create `settings.py` with Google + JWT secrets.
* Start FastAPI (`uvicorn api.app:app`), then Streamlit (`streamlit run main.py`).
* Ensure Ollama or another LLM provider is available for the agent, or adapt the agent to a different provider.
* Keep credentials safe and test OAuth redirect URIs thoroughly.

---

If you want, I can:

* produce a ready-to-drop `settings.example.py` file with placeholders,
* generate Docker Compose to run API + a mock LLM or an OpenAI adaptation,
* or update `email_agent/agent.py` to use OpenAI instead of Ollama and show you the exact code changes.

Which of the above would you like me to do next? (I can just pick one and implement it — no waiting required.)

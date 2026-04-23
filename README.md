# LabBuddy — Smart Lab Protocol Assistant

> *"Describe your experiment, we document it!"*

**LabBuddy** is a voice-powered lab experiment protocol assistant built on the **Azure Voice Live API**. It listens while a researcher dictates their experiment, automatically extracts structured protocol fields in real-time using an **Azure OpenAI GPT-4o** extraction agent, and produces exportable artifacts (JSON, Excel, transcript, audio).

LabBuddy supports bilingual voice sessions (German / English) and ships with two ready-to-use demo profiles for Adhesive Technologies and Hair Care R&D labs — both fully customizable.

---

## ✨ Features

- **Real-time voice protocol recording** — speak naturally; LabBuddy listens and extracts
- **Bilingual (DE / EN)** — language toggle switches UI, prompts, and extraction schema
- **Live field extraction** — structured protocol fields fill in the sidebar as you talk
- **SYSTEM CALL commands** — "SYSTEM CALL What is missing?" triggers an on-demand summary
- **Export** — download transcript (`.txt`), recording (`.wav`), fields (`.json` + `.xlsx`)
- **LIMS Preview** *(Medium Tech mode)* — mock LIMS submission dialog with protocol ID
- **Agent Activity Feed** *(Medium Tech mode)* — see the multi-agent workflow in action
- **One-click Azure deploy** — `azd up` provisions everything via Bicep
- **In-app settings panel** — enter your Azure endpoint and API key directly in the browser, no file editing needed

---

## Architecture

```
Browser (HTML/JS)           Backend (FastAPI / Python)            Azure Cloud
┌──────────────┐    WS     ┌────────────────────────┐    SDK    ┌──────────────────┐
│ Mic → PCM16  │◄─────────►│ voice_handler.py        │◄─────────►│ Voice Live API   │
│ Speaker      │   JSON    │ (Voice Live SDK bridge)  │          │ STT + LLM + TTS  │
│ Fields Panel │           │                         │          └──────────────────┘
│ DE/EN Toggle │           │ agent.py                │──────────►┌──────────────────┐
└──────────────┘           │ (Protocol Extraction    │  OpenAI   │ Azure OpenAI     │
                           │  Agent)                 │   SDK     │ GPT-4o           │
                           │ storage.py              │──────────►┌──────────────────┐
                           │ (Local export)          │          │ Azure Blob Store │
                           └─────────────────────────┘          └──────────────────┘
```

### Key Design Decisions

- **Azure Voice Live API** — STT + LLM reasoning + TTS in a single managed WebSocket
- **Protocol Extraction Agent** — after every assistant turn, a separate GPT-4o call extracts structured JSON fields
- **Config-driven profiles** — all field definitions, labels, and LIMS settings live in `backend/configs/*.json`
- **Managed Identity** — zero API keys in production (`DefaultAzureCredential`)
- **API key fallback** — for local dev, set `AZURE_VOICELIVE_API_KEY` or use the in-app settings panel

---

## 🚀 Quick Start

### Option 1 — GitHub Codespaces (easiest)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/abeckDev/LabBuddy-SmartLabProtocollationAssistant)

Inside the Codespace terminal:

```bash
azd auth login
azd up
```

`azd up` provisions **everything**: Azure AI Services (with GPT-4o deployment), Container App, Storage, Container Registry, and Managed Identity with RBAC.

### Option 2 — Local with `azd up`

**Prerequisites:** [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) · [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
git clone https://github.com/abeckDev/LabBuddy-SmartLabProtocollationAssistant.git
cd LabBuddy-SmartLabProtocollationAssistant
azd auth login
azd up
```

### Option 3 — Init from azd template

```bash
azd init -t abeckDev/LabBuddy-SmartLabProtocollationAssistant
azd up
```

> **What `azd up` provisions:**
> | Resource | Purpose |
> |----------|---------|
> | Azure AI Services (S0) | Voice Live API + GPT-4o extraction model |
> | Azure Container App | Runs the FastAPI backend + static frontend |
> | Azure Container Registry | Stores the Docker image |
> | Azure Blob Storage | Persists session artifacts |
> | Managed Identity + RBAC | Zero API keys — Cognitive Services User + Storage Blob Data Contributor |

---

## 💻 Local Development

### Option A — Using the In-App Settings Panel (no `.env` file needed)

1. Start the backend (see below)
2. Open [http://localhost:8000](http://localhost:8000)
3. Click the **⚙️** button in the top-right corner
4. Enter your **Azure AI Services Endpoint** and (optionally) your **API Key**
5. Click **Save** — settings are stored in your browser's localStorage
6. Click **Start** to begin a session

### Option B — `.env` file

```bash
git clone https://github.com/abeckDev/LabBuddy-SmartLabProtocollationAssistant.git
cd LabBuddy-SmartLabProtocollationAssistant

# 1. Copy and edit the env file
cp .env.sample .env
# Edit .env: at minimum set AZURE_VOICELIVE_ENDPOINT

# 2. Authenticate to Azure (for DefaultAzureCredential — skip if using API key)
az login

# 3. Install Python dependencies
cd backend
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt

# 4. Run the server
python app.py
# Open http://localhost:8000
```

### Option C — Docker Compose

```bash
cp .env.sample .env
# Edit .env with your Azure endpoint
docker compose up
# Open http://localhost:8000
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_VOICELIVE_ENDPOINT` | Yes* | Azure AI Services endpoint (Voice Live + OpenAI) |
| `AZURE_VOICELIVE_API_KEY` | No | API key — leave empty to use `az login` / Managed Identity |
| `AZURE_OPENAI_ENDPOINT` | No | Separate OpenAI endpoint (defaults to `AZURE_VOICELIVE_ENDPOINT`) |
| `AZURE_OPENAI_DEPLOYMENT` | No | GPT-4o deployment name (default: `gpt-4o`) |
| `AZURE_STORAGE_ENDPOINT` | No | Blob Storage endpoint for cloud artifact persistence |
| `VOICELIVE_MODEL` | No | Voice Live model (default: `gpt-4o`) |
| `VOICELIVE_VOICE` | No | TTS voice (default: `de-DE-SeraphinaMultilingualNeural`) |
| `DEMO_CONFIG` | No | Default demo profile (default: `adhesive_technologies`) |

*\*Can also be provided via the in-app ⚙️ Settings panel instead of an env variable.*

> **Tip:** When deploying with `azd up`, all environment variables are set automatically by the Bicep templates — no `.env` file is needed.

### Demo Profiles

LabBuddy ships with two example profiles in `backend/configs/`:

| Profile | File | Use case |
|---------|------|----------|
| Adhesive Technologies Lab | `adhesive_technologies.json` | Formulation, analytics, adhesive experiments |
| Consumer Brands — Hair Care | `consumer_brands_haircare.json` | Shampoo/conditioner formulation and sensory tests |

**To create a custom profile**, copy one of the existing JSON files, modify the `company`, `division`, `extraction_fields`, `required_fields`, `field_labels`, and `lims` sections, and place it in `backend/configs/`. The new profile will appear automatically in the UI dropdown on next startup.

---

## Prerequisites

| Scenario | Requirements |
|----------|-------------|
| **Cloud deploy (`azd up`)** | Azure subscription, `azd` CLI, Docker Desktop |
| **Local dev (API key)** | Python 3.10+, Azure AI Services resource with Voice Live access |
| **Local dev (Managed Identity)** | Python 3.10+, `az login`, same resource |

> **Azure region:** Voice Live API is available in `swedencentral`, `eastus2`, and selected other regions. Check the [Azure docs](https://learn.microsoft.com/azure/ai-services/speech-service/regions) for the latest list.

---

## Project Structure

```
LabBuddy-SmartLabProtocollationAssistant/
├── frontend/                       # Static frontend (served by FastAPI)
│   ├── index.html                  # Main UI (DE/EN toggle, settings panel)
│   ├── style.css                   # Styles
│   ├── app.js                      # WebSocket client, audio, settings
│   ├── audio-capture-worklet.js    # Mic → PCM16 24 kHz AudioWorklet
│   └── audio-playback-worklet.js   # PCM16 → speakers AudioWorklet
│
├── backend/                        # Python backend
│   ├── app.py                      # FastAPI: WS /ws/{id}, REST, static
│   ├── voice_handler.py            # Voice Live SDK bridge + system prompts
│   ├── agent.py                    # Protocol Extraction Agent (GPT-4o)
│   ├── extraction_schema.py        # Default field schema (overridden by config)
│   ├── config_loader.py            # Demo profile loader
│   ├── configs/                    # Demo profiles (JSON)
│   │   ├── adhesive_technologies.json
│   │   └── consumer_brands_haircare.json
│   ├── storage.py                  # Local export (+ optional Blob Storage)
│   ├── mock_data.py                # Medium Tech mock data
│   └── requirements.txt
│
├── docs/                           # Documentation & diagrams
├── infra/                          # Bicep IaC (azd template)
├── Dockerfile                      # Single-container image
├── docker-compose.yml              # Local dev compose
├── azure.yaml                      # azd manifest
└── .env.sample                     # Config template
```

---

## 🗺️ Roadmap / Medium Tech Preview

The UI includes a **Medium Tech mode** (🚀 toggle in header) that previews upcoming capabilities:

- **Lab Camera** — capture lab setup images for vision analysis
- **LIMS Integration** — one-click submission to your Laboratory Information Management System
- **SOP Suggestions** — real-time Standard Operating Procedure cards based on transcript keywords
- **Material Lookups** — live material/reagent database lookups
- **Agent Activity Feed** — transparent view of the multi-agent extraction workflow

These features are **simulated** in the current release and marked with a `PREVIEW` badge.

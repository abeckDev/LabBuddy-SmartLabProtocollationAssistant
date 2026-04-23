"""
LabBuddy — FastAPI application.
Serves the frontend, handles WebSocket connections, and provides REST endpoints.
"""

import json
import logging
import os
import random
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from azure.core.credentials import AzureKeyCredential
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from voice_handler import VoiceLiveHandler
from mock_data import VISION_RESPONSES
from config_loader import load_config, list_available_configs, get_default_config_name, get_config_for_session

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "server.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── State ────────────────────────────────────────────────────────────────
_handlers: Dict[str, VoiceLiveHandler] = {}
_credential: Optional[Any] = None


def _get_credential(api_key: str | None = None) -> Any:
    global _credential
    # Use caller-supplied key if provided
    if api_key:
        return AzureKeyCredential(api_key)
    if _credential is None:
        env_api_key = os.getenv("AZURE_VOICELIVE_API_KEY")
        if env_api_key:
            _credential = AzureKeyCredential(env_api_key)
            logger.info("Using API key credential")
        else:
            _credential = DefaultAzureCredential()
            logger.info("Using DefaultAzureCredential (Managed Identity)")
    return _credential


# ── App lifecycle ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LabBuddy server starting …")
    yield
    for cid in list(_handlers):
        await _handlers[cid].stop()
    _handlers.clear()
    if _credential and hasattr(_credential, "close"):
        await _credential.close()
    logger.info("Server shut down.")


app = FastAPI(title="LabBuddy - Smart Lab Protocol Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST endpoints (before static mount) ─────────────────────────────────
@app.get("/api/setup-status")
async def setup_status():
    """Return whether the required Azure endpoint is configured via environment variables."""
    return {
        "configured": bool(os.getenv("AZURE_VOICELIVE_ENDPOINT")),
        "has_api_key": bool(os.getenv("AZURE_VOICELIVE_API_KEY")),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "labbuddy"}


@app.get("/api/config")
async def get_config():
    default_name = get_default_config_name()
    try:
        cfg = load_config(default_name)
    except Exception:
        cfg = {}
    return {
        "model": os.getenv("VOICELIVE_MODEL", "gpt-4o"),
        "voice": os.getenv("VOICELIVE_VOICE", "de-DE-SeraphinaMultilingualNeural"),
        "default_config": default_name,
        "lims_name": cfg.get("lims", {}).get("name", "Albert"),
    }


@app.get("/api/configs")
async def get_configs():
    """Return all available demo config profiles."""
    return {"configs": list_available_configs(), "default": get_default_config_name()}


@app.get("/api/configs/{config_name}")
async def get_config_detail(config_name: str):
    """Return full config for frontend (field labels, LIMS name, sections, etc.)."""
    try:
        cfg = load_config(config_name)
        return {
            "name": config_name,
            "profile_name": cfg.get("profile_name", {}),
            "company": cfg.get("company", ""),
            "division": cfg.get("division", ""),
            "lims": cfg.get("lims", {}),
            "field_labels": cfg.get("field_labels", {}),
            "required_fields": cfg.get("required_fields", []),
            "lims_sections": cfg.get("lims_sections", {}),
            "extraction_fields": list(cfg.get("extraction_fields", {}).keys()),
        }
    except FileNotFoundError:
        return JSONResponse({"error": f"Config '{config_name}' not found"}, status_code=404)


@app.post("/api/lims/submit")
async def lims_submit(payload: dict):
    """Mock endpoint: accept protocol data and return a fake LIMS protocol ID."""
    config_name = payload.pop("_config_name", None)
    try:
        cfg = get_config_for_session(config_name)
        lims_name = cfg.get("lims", {}).get("name", "LIMS")
        url_template = cfg.get("lims", {}).get("url_template", "https://lims.example.com/protocols/{protocol_id}")
    except Exception:
        lims_name = "LIMS"
        url_template = "https://lims.example.com/protocols/{protocol_id}"

    now = datetime.now(timezone.utc)
    protocol_id = f"LB-{now.year}-{now.strftime('%m%d')}-{random.randint(1, 999):03d}"
    logger.info(f"Mock LIMS submit — assigned protocol ID {protocol_id} ({lims_name})")
    return {
        "status": "success",
        "protocol_id": protocol_id,
        "message": f"Protocol {protocol_id} submitted to {lims_name} LIMS successfully.",
        "lims_url": url_template.format(protocol_id=protocol_id),
    }


@app.get("/api/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    """Serve exported session artifacts."""
    # Sanitize inputs to prevent path traversal
    safe_session = Path(session_id).name
    safe_filename = Path(filename).name
    file_path = Path(__file__).parent / "exports" / safe_session / safe_filename

    if not file_path.exists() or not file_path.is_file():
        return JSONResponse({"error": "File not found"}, status_code=404)

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="application/octet-stream",
    )


@app.get("/api/export/{session_id}")
async def export_session_http(session_id: str):
    """Return download links for a previously exported session."""
    safe_session = Path(session_id).name
    export_dir = Path(__file__).parent / "exports" / safe_session
    if not export_dir.exists() or not export_dir.is_dir():
        return JSONResponse({"type": "error", "message": "Session not found"}, status_code=404)

    base = f"/api/download/{safe_session}"
    files = {}
    if (export_dir / "transcript.txt").exists():
        files["transcript"] = f"{base}/transcript.txt"
    if (export_dir / "conversation.wav").exists():
        files["audio"] = f"{base}/conversation.wav"
    if (export_dir / "extracted_fields.json").exists():
        files["json"] = f"{base}/extracted_fields.json"
    if (export_dir / "extracted_fields.xlsx").exists():
        files["xlsx"] = f"{base}/extracted_fields.xlsx"

    return {"type": "export_ready", "files": files}


# ── WebSocket endpoint ──────────────────────────────────────────────────
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    logger.info(f"Client {client_id} connected")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await _handle_message(client_id, message, websocket)
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        await _cleanup_client(client_id)


async def _handle_message(client_id: str, message: dict, websocket: WebSocket):
    msg_type = message.get("type")

    if msg_type == "start_session":
        await _start_session(client_id, message, websocket)
    elif msg_type == "stop_session":
        await _stop_session(client_id, websocket)
    elif msg_type == "audio_chunk":
        handler = _handlers.get(client_id)
        if handler:
            await handler.send_audio(message.get("data", ""))
    elif msg_type == "interrupt":
        handler = _handlers.get(client_id)
        if handler:
            await handler.interrupt()
    elif msg_type == "export_session":
        await _export_session(client_id, websocket)
    elif msg_type == "vision_capture":
        await _handle_vision_capture(client_id, websocket)
    else:
        logger.warning(f"Unknown message type from {client_id}: {msg_type}")


async def _start_session(client_id: str, config: dict, websocket: WebSocket):
    try:
        # Accept endpoint/key overrides from the client message (for local/UI-configured setup)
        endpoint = (
            config.get("endpoint")
            or os.getenv("AZURE_VOICELIVE_ENDPOINT")
        )
        if not endpoint:
            raise ValueError(
                "Azure AI Services endpoint is not configured. "
                "Set AZURE_VOICELIVE_ENDPOINT or provide it via the settings panel."
            )

        api_key = config.get("api_key") or None
        credential = _get_credential(api_key)
        session_id = str(uuid.uuid4())[:8]

        # Accept OpenAI endpoint/deployment overrides from client
        openai_endpoint = (
            config.get("openai_endpoint")
            or os.getenv("AZURE_OPENAI_ENDPOINT", "")
            or endpoint
        )
        openai_deployment = (
            config.get("openai_deployment")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.3-chat")
        )

        async def send_to_client(msg: dict):
            try:
                await websocket.send_text(json.dumps(msg))
            except Exception as e:
                logger.error(f"Failed to send to {client_id}: {e}")

        # Tear down previous handler
        if client_id in _handlers:
            await _handlers[client_id].stop()

        # Load demo config for this session
        config_name = config.get("config_name", None)
        try:
            session_config = get_config_for_session(config_name)
        except Exception as e:
            logger.warning(f"Failed to load config '{config_name}', using default: {e}")
            session_config = get_config_for_session(None)

        handler = VoiceLiveHandler(
            session_id=session_id,
            endpoint=endpoint,
            credential=credential,
            send_message=send_to_client,
            model=config.get("model", os.getenv("VOICELIVE_MODEL", "gpt-4o")),
            voice=config.get("voice", os.getenv("VOICELIVE_VOICE",
                             "de-DE-SeraphinaMultilingualNeural")),
            openai_endpoint=openai_endpoint,
            openai_deployment=openai_deployment,
            language=config.get("language", "de"),
            mode=config.get("mode", "low"),
            config=session_config,
        )
        _handlers[client_id] = handler
        await handler.start()
        logger.info(f"Session {session_id} started for {client_id}")

    except Exception as e:
        logger.error(f"Failed to start session for {client_id}: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass


async def _stop_session(client_id: str, websocket: WebSocket):
    handler = _handlers.pop(client_id, None)
    session_id = None
    if handler:
        session_id = handler.session_id
        # Auto-export artifacts before stopping
        try:
            await handler.export_session()
            logger.info(f"Auto-export completed for {client_id} (session {session_id})")
        except Exception as e:
            logger.error(f"Auto-export failed for {client_id}: {e}")
        await handler.stop()
    try:
        await websocket.send_text(json.dumps({"type": "session_stopped", "sessionId": session_id}))
    except Exception:
        pass


async def _export_session(client_id: str, websocket: WebSocket):
    handler = _handlers.get(client_id)
    if not handler:
        await websocket.send_text(json.dumps({
            "type": "error", "message": "No active session to export"
        }))
        return

    try:
        urls = await handler.export_session()
        await websocket.send_text(json.dumps({
            "type": "export_ready",
            "files": urls,
        }))
        logger.info(f"Export completed for {client_id}")
    except Exception as e:
        logger.error(f"Export failed for {client_id}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error", "message": f"Export failed: {e}"
        }))


async def _handle_vision_capture(client_id: str, websocket: WebSocket):
    """Handle a vision_capture message: return a mock lab observation."""
    analysis = random.choice(VISION_RESPONSES)
    logger.info(f"Mock vision analysis for {client_id}")
    try:
        await websocket.send_text(json.dumps({
            "type": "vision_result",
            "text": analysis,
        }))
    except Exception as e:
        logger.error(f"Failed to send vision result to {client_id}: {e}")


async def _cleanup_client(client_id: str):
    handler = _handlers.pop(client_id, None)
    if handler:
        await handler.stop()


# ── Static files (frontend) — mounted last ──────────────────────────────
_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="static")
    logger.info(f"Serving frontend from {_frontend_dir}")


# ── Entrypoint ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

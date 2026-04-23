"""
LabBuddy — Voice Live Handler.
Bridges browser WebSocket <-> Azure Voice Live SDK.
Uses a separate Protocol Extraction Agent (Azure OpenAI SDK) after each turn to extract
fields from the transcript and feeds missing-field hints back into Voice Live.
"""

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

from azure.ai.voicelive.aio import connect
from azure.ai.voicelive.models import (
    AudioEchoCancellation,
    AudioInputTranscriptionOptions,
    AudioNoiseReduction,
    AzureSemanticVad,
    AzureStandardVoice,
    InputAudioFormat,
    InputTextContentPart,
    MessageItem,
    Modality,
    OutputAudioFormat,
    RequestSession,
    ServerEventType,
)

from agent import ExtractionAgent
from extraction_schema import ALL_FIELDS, get_fields_from_config, get_required_from_config
from mock_data import AGENT_ACTIVITY_SEQUENCES
from storage import SessionStorage

logger = logging.getLogger(__name__)

SendMessageFn = Callable[[dict], Coroutine[Any, Any, None]]

SYSTEM_PROMPTS = {
    "de": """\
You are LabBuddy, a silent lab protocol recording assistant for \
{company}.

LANGUAGE: When you DO speak, speak ONLY in German.

YOUR TASK:
You are in PASSIVE LISTENING MODE. Your job is to silently listen while the \
researcher dictates their experiment protocol. You are NOT a conversational \
assistant — you are a recording tool.

CRITICAL RULES:
- Do NOT speak, ask questions, moderate, confirm, summarize, or respond in any way \
unless the researcher explicitly says "SYSTEM CALL".
- Do NOT greet, prompt, encourage, or guide the researcher.
- Do NOT say "Notiert", "Super", "Alles klar" or any acknowledgment.
- Stay completely silent. Let the researcher talk freely.
- The extraction of structured data happens automatically in the background — \
you do not need to do anything.

SYSTEM CALL PROTOCOL:
When the researcher says "SYSTEM CALL" followed by a request, you MUST respond \
to that specific request. Examples:
- "SYSTEM CALL Was fehlt noch?" → List the fields that are still missing.
- "SYSTEM CALL Zusammenfassung" → Summarize all captured information so far.
- "SYSTEM CALL Protokoll abschließen" → Confirm completion and thank them for using LabBuddy.
After responding to a SYSTEM CALL, immediately return to silent listening mode. \
Do NOT ask follow-up questions after a SYSTEM CALL response.
""",
    "en": """\
You are LabBuddy, a silent lab protocol recording assistant for \
{company}.

LANGUAGE: When you DO speak, speak ONLY in English.

YOUR TASK:
You are in PASSIVE LISTENING MODE. Your job is to silently listen while the \
researcher dictates their experiment protocol. You are NOT a conversational \
assistant — you are a recording tool.

CRITICAL RULES:
- Do NOT speak, ask questions, moderate, confirm, summarize, or respond in any way \
unless the researcher explicitly says "SYSTEM CALL".
- Do NOT greet, prompt, encourage, or guide the researcher.
- Do NOT say "Noted", "Great", "Perfect" or any acknowledgment.
- Stay completely silent. Let the researcher talk freely.
- The extraction of structured data happens automatically in the background — \
you do not need to do anything.

SYSTEM CALL PROTOCOL:
When the researcher says "SYSTEM CALL" followed by a request, you MUST respond \
to that specific request. Examples:
- "SYSTEM CALL What information is missing?" → List the fields that are still missing.
- "SYSTEM CALL Summarize input so far" → Summarize all captured information so far.
- "SYSTEM CALL Finalize protocol" → Confirm completion. Thank them for using LabBuddy.
After responding to a SYSTEM CALL, immediately return to silent listening mode. \
Do NOT ask follow-up questions after a SYSTEM CALL response.

""",
}

GREETING_PROMPTS = {
    "de": (
        "Sage nur: 'Bereit zur Protokollierung.' — nichts weiter. "
        "Keine Begrüßung, keine Fragen, kein Smalltalk."
    ),
    "en": (
        "Say only: 'Ready for protocollation.' — nothing else. "
        "No greeting, no questions, no small talk."
    ),
}

class VoiceLiveHandler:
    """Manages a single Voice Live session for one WebSocket client.

    Flow per turn:
      1. Voice Live STT → user transcript
      2. Voice Live LLM → assistant speaks follow-up (TTS)
      3. After RESPONSE_DONE → Extraction Agent processes full transcript
      4. Agent returns extracted fields + missing required fields
      5. Missing-field hint injected as system message into Voice Live
      6. Loop until all required fields are filled
    """

    def __init__(
        self,
        session_id: str,
        endpoint: str,
        credential: Any,
        send_message: SendMessageFn,
        model: str = "gpt-4o",
        voice: str = "de-DE-SeraphinaMultilingualNeural",
        openai_endpoint: str = "",
        openai_deployment: str = "gpt-5.3-chat",
        language: str = "de",
        mode: str = "low",
        config: dict | None = None,
    ):
        self.session_id = session_id
        self.endpoint = endpoint
        self.credential = credential
        self.send = send_message
        self.model = model
        self.voice_name = voice
        self.language = language if language in SYSTEM_PROMPTS else "de"
        self.mode = mode if mode in ("low", "medium") else "low"
        self.config = config

        # Derive field lists from config or defaults
        if config:
            self._all_fields = get_fields_from_config(config)
            self._company = config.get("company", "Your Organization")
        else:
            self._all_fields = ALL_FIELDS
            self._company = "Your Organization"

        # Extraction Agent (Azure OpenAI SDK — can use a different endpoint)
        self.agent = ExtractionAgent(
            endpoint=openai_endpoint or endpoint,
            credential=credential,
            deployment=openai_deployment,
            language=self.language,
            config=config,
        )

        # Session state
        self.extracted_fields: dict = {k: None for k in self._all_fields}
        self.transcript: list[dict] = []
        self.user_audio_buffer = bytearray()
        self.assistant_audio_buffer = bytearray()
        self._assistant_text = ""
        self._all_complete = False

        self.connection = None
        self.is_running = False
        self._event_task: Optional[asyncio.Task] = None

    # -- Public API -------------------------------------------------------

    async def start(self):
        self.is_running = True
        self._event_task = asyncio.create_task(self._run())

    async def send_audio(self, audio_base64: str):
        """Forward base64 PCM16 audio from the browser to Voice Live."""
        if self.connection:
            try:
                # Also record for export
                raw = base64.b64decode(audio_base64)
                self.user_audio_buffer.extend(raw)
                await self.connection.input_audio_buffer.append(audio=audio_base64)
            except Exception as e:
                logger.error(f"[{self.session_id}] Audio forward error: {e}")

    async def interrupt(self):
        if self.connection:
            try:
                await self.connection.response.cancel()
            except Exception:
                pass

    async def stop(self):
        self.is_running = False
        if self._event_task and not self._event_task.done():
            self._event_task.cancel()
            try:
                await self._event_task
            except (asyncio.CancelledError, Exception):
                pass
        self.connection = None
        await self.agent.close()
        logger.info(f"[{self.session_id}] Handler stopped")

    async def export_session(self) -> dict:
        combined_audio = bytes(self.user_audio_buffer) + bytes(self.assistant_audio_buffer)
        storage = SessionStorage(self.session_id, config=self.config)
        clean_fields = {k: v for k, v in self.extracted_fields.items()
                        if v is not None and v != ""}
        return await storage.save_artifacts(
            transcript=self.transcript,
            audio_bytes=combined_audio,
            fields=clean_fields,
        )

    # -- Connection + session setup ---------------------------------------

    async def _run(self):
        try:
            logger.info(
                f"[{self.session_id}] Connecting to Voice Live "
                f"(model={self.model}, voice={self.voice_name})"
            )
            async with connect(
                endpoint=self.endpoint,
                credential=self.credential,
                model=self.model,
                api_version="2025-10-01",
            ) as connection:
                self.connection = connection
                await self._configure_session(connection)
                await self._process_events(connection)

        except asyncio.CancelledError:
            logger.info(f"[{self.session_id}] Event loop cancelled")
        except Exception as e:
            logger.error(f"[{self.session_id}] Voice Live error: {e}")
            await self.send({"type": "error", "message": str(e)})
        finally:
            self.is_running = False
            self.connection = None

    async def _configure_session(self, connection):
        session_config = RequestSession(
            modalities=[Modality.TEXT, Modality.AUDIO],
            instructions=SYSTEM_PROMPTS[self.language].format(company=self._company),
            input_audio_format=InputAudioFormat.PCM16,
            output_audio_format=OutputAudioFormat.PCM16,
            voice=AzureStandardVoice(name=self.voice_name),
            turn_detection=AzureSemanticVad(
                silence_duration_ms=1500,
                interrupt_response=False,
            ),
            input_audio_transcription=AudioInputTranscriptionOptions(
                model="azure-speech",
            ),
            input_audio_noise_reduction=AudioNoiseReduction(
                type="azure_deep_noise_suppression"
            ),
            input_audio_echo_cancellation=AudioEchoCancellation(),
            temperature=0.7,
        )
        await connection.session.update(session=session_config)
        logger.info(f"[{self.session_id}] Session config sent (using external extraction agent)")

    # -- Event loop -------------------------------------------------------

    async def _process_events(self, connection):
        async for event in connection:
            if not self.is_running:
                break
            try:
                await self._handle_event(event, connection)
            except Exception as e:
                logger.error(f"[{self.session_id}] Event error: {e}")

    async def _handle_event(self, event, connection):
        t = event.type

        # -- Session ready ------------------------------------------------
        if t == ServerEventType.SESSION_UPDATED:
            await self.send({"type": "session_started", "sessionId": self.session_id})
            await self.send({"type": "status", "state": "listening"})
            # Trigger greeting
            await self._send_greeting(connection)

        # -- User starts speaking (barge-in) ------------------------------
        elif t == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
            await self.send({"type": "status", "state": "listening"})

        # -- User stops speaking ------------------------------------------
        elif t == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
            await self.send({"type": "status", "state": "thinking"})

        # -- User transcript (final) --------------------------------------
        elif t == ServerEventType.CONVERSATION_ITEM_INPUT_AUDIO_TRANSCRIPTION_COMPLETED:
            text = getattr(event, "transcript", "")
            if text:
                self.transcript.append({
                    "role": "user",
                    "text": text,
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                })
                await self.send({"type": "transcript", "role": "user",
                                 "text": text, "isFinal": True})

        # -- Response lifecycle -------------------------------------------
        elif t == ServerEventType.RESPONSE_CREATED:
            await self.send({"type": "status", "state": "speaking"})

        elif t == ServerEventType.RESPONSE_AUDIO_DELTA:
            if hasattr(event, "delta") and event.delta:
                audio_b64 = base64.b64encode(event.delta).decode("utf-8")
                self.assistant_audio_buffer.extend(event.delta)
                await self.send({
                    "type": "audio_data",
                    "data": audio_b64,
                    "sampleRate": 24000,
                })

        elif t == ServerEventType.RESPONSE_AUDIO_TRANSCRIPT_DELTA:
            delta = getattr(event, "delta", "")
            if delta:
                self._assistant_text += delta

        elif t == ServerEventType.RESPONSE_DONE:
            if self._assistant_text:
                self.transcript.append({
                    "role": "assistant",
                    "text": self._assistant_text,
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                })
                await self.send({
                    "type": "transcript",
                    "role": "assistant",
                    "text": self._assistant_text,
                    "isFinal": True,
                })
                self._assistant_text = ""
            await self.send({"type": "status", "state": "listening"})

            # ── EXTRACTION AGENT: run after each completed turn ──────────
            await self._run_extraction_agent(connection)

        # -- Errors -------------------------------------------------------
        elif t == ServerEventType.ERROR:
            error_msg = getattr(event, "error", None)
            message = getattr(error_msg, "message", str(error_msg)) if error_msg else str(event)
            code = getattr(error_msg, "code", "") if error_msg else ""

            if code == "response_cancel_not_active" or "no active response" in message.lower():
                return

            logger.error(f"[{self.session_id}] Voice Live error: {message}")
            await self.send({"type": "error", "message": message})

    # -- Extraction Agent integration -------------------------------------

    async def _run_extraction_agent(self, connection):
        """Call the extraction agent with the full transcript, update fields,
        and inject missing-field hints into the Voice Live conversation."""
        if self._all_complete or len(self.transcript) < 2:
            return  # Skip on greeting turn or after completion

        # In Medium Tech mode, send agent activity feed first
        if self.mode == "medium":
            asyncio.create_task(self._send_agent_activity())

        try:
            result = await self.agent.extract_fields(
                transcript=self.transcript,
                current_fields=self.extracted_fields,
            )

            self.extracted_fields = result["fields"]
            missing = result["all_missing"]
            missing_required = result["missing_required"]
            completion = result["completion"]

            # Notify browser with updated fields
            await self.send({
                "type": "fields_update",
                "fields": self.extracted_fields,
                "completion": completion,
                "missingRequired": missing_required,
                "allMissing": missing,
            })

            # In Medium Tech mode, send mock SOP/material suggestions
            if self.mode == "medium":
                lookups = self.agent.generate_mock_lookups(
                    transcript=self.transcript,
                    extracted_fields=self.extracted_fields,
                )
                for sop in lookups["sop_suggestions"]:
                    await self.send({"type": "sop_suggestion", "data": sop})
                for mat in lookups["material_lookups"]:
                    await self.send({"type": "material_lookup", "data": mat})

            if not missing:
                self._all_complete = True
                await self.send({"type": "session_complete"})
            else:
                logger.info(
                    f"[{self.session_id}] Agent: {completion}% complete, "
                    f"missing: {missing}"
                )

        except Exception as e:
            logger.error(f"[{self.session_id}] Extraction agent error: {e}", exc_info=True)
            await self.send({"type": "error", "message": f"Extraction error: {e}"})

    async def _send_agent_activity(self):
        """Send simulated agent activity messages with realistic timing (Medium Tech only)."""
        try:
            for step in AGENT_ACTIVITY_SEQUENCES:
                await asyncio.sleep(step["delay_ms"] / 1000)
                await self.send({
                    "type": "agent_activity",
                    "icon": step["icon"],
                    "agent": step["agent"],
                    "message": step["message"],
                })
        except Exception as e:
            logger.debug(f"[{self.session_id}] Agent activity send error: {e}")

    # -- Greeting ---------------------------------------------------------

    async def _send_greeting(self, connection):
        try:
            await connection.conversation.item.create(
                item=MessageItem(
                    role="system",
                    content=[InputTextContentPart(
                        text=GREETING_PROMPTS[self.language]
                    )],
                )
            )
            await connection.response.create()
            logger.info(f"[{self.session_id}] Greeting triggered")
        except Exception as e:
            logger.warning(f"[{self.session_id}] Greeting failed: {e}")

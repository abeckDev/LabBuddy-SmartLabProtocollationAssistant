"""
LabBuddy — Protocol Extraction Agent.
Uses Azure OpenAI SDK to extract structured lab protocol fields from conversation transcript.
Runs after each user turn as a side-channel for reliable structured extraction.
"""

import json
import logging
from typing import Any, Optional

from openai import AsyncAzureOpenAI
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider

from extraction_schema import (
    EXTRACTION_SCHEMA, get_missing_fields, get_all_missing_fields,
    get_completion_percentage, get_schema_descriptions,
    build_schema_from_config, get_fields_from_config, get_required_from_config,
)
from mock_data import SOP_SUGGESTIONS, MATERIAL_LOOKUPS

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
You are a data extraction agent for {company}.

TASK:
Analyze the conversation transcript below and extract ALL lab experiment protocol details \
mentioned by the researcher into a structured JSON object.

RULES:
1. Only extract information explicitly stated by the researcher — never guess or infer.
2. Keep property values in the SAME language the researcher is speaking \
   (German values if speaking German, English if speaking English).
3. If a field was not mentioned, set it to null.
4. If the researcher corrects or updates a previously stated value, use the latest value.
5. Return ONLY the JSON object — no explanation, no markdown.

FIELDS TO EXTRACT:
{schema}

CONVERSATION TRANSCRIPT:
{transcript}

Respond with a JSON object containing only the fields that have been mentioned. \
Use null for fields not yet discussed.
"""


class ExtractionAgent:
    """Agent that extracts structured lab protocol fields from conversation transcript."""

    def __init__(self, endpoint: str, credential: Any, deployment: str = "gpt-5.3", language: str = "de", config: dict | None = None):
        self.deployment = deployment
        self.language = language if language in ("de", "en") else "de"
        self.config = config

        # Build config-driven schema, fields, and required lists
        if config:
            self._schema = build_schema_from_config(config)
            self._all_fields = get_fields_from_config(config)
            self._required_fields = get_required_from_config(config)
            self._company = config.get("company", "Your Organization")
            self._sop_suggestions = config.get("sop_suggestions", SOP_SUGGESTIONS)
            self._material_lookups = config.get("material_lookups", MATERIAL_LOOKUPS)
        else:
            self._schema = EXTRACTION_SCHEMA
            self._all_fields = list(EXTRACTION_SCHEMA["properties"].keys())
            self._required_fields = ["researcherName", "experimentTitle", "experimentType", "experimentDate", "rawMaterials", "procedureSteps", "result"]
            self._company = "Your Organization"
            self._sop_suggestions = SOP_SUGGESTIONS
            self._material_lookups = MATERIAL_LOOKUPS

        # Build Azure OpenAI client with token-based auth
        if hasattr(credential, "key"):
            # AzureKeyCredential — use API key
            self.client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_key=credential.key,
                api_version="2024-12-01-preview",
            )
        else:
            # DefaultAzureCredential — use token provider
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
            self.client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version="2024-12-01-preview",
            )

    async def extract_fields(
        self,
        transcript: list[dict],
        current_fields: dict,
    ) -> dict:
        """
        Process the full conversation transcript and extract lab protocol fields.

        Returns dict with:
            - fields: dict of all extracted field values
            - missing_required: list of required fields still empty
            - completion: float percentage
            - follow_up_hint: str suggested next question topic
        """
        if not transcript:
            return {
                "fields": current_fields,
                "missing_required": get_missing_fields(current_fields, self._required_fields),
                "completion": get_completion_percentage(current_fields, self._all_fields),
                "follow_up_hint": "",
            }

        # Build transcript text
        transcript_text = "\n".join(
            f"[{entry.get('role', 'unknown').upper()}]: {entry.get('text', '')}"
            for entry in transcript
        )

        # Build schema description for the prompt (in session language)
        schema_desc = get_schema_descriptions(self.language, self._schema)

        prompt = EXTRACTION_PROMPT.format(
            company=self._company,
            schema=schema_desc,
            transcript=transcript_text,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "You are a precise data extraction agent. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=2000,
            )

            raw = response.choices[0].message.content
            extracted = json.loads(raw)

            # Merge: only update fields that are non-null in extraction
            merged = dict(current_fields)
            for key, value in extracted.items():
                if key in merged and value is not None and value != "":
                    merged[key] = value

            missing = get_missing_fields(merged, self._required_fields)
            all_missing = get_all_missing_fields(merged, self._all_fields)
            completion = get_completion_percentage(merged, self._all_fields)

            # Generate a hint about what to ask next (from ALL unfilled fields)
            follow_up = ""
            if all_missing:
                # Build labels from schema descriptions (config-driven)
                field_labels = {}
                for key in self._all_fields:
                    field_labels[key] = get_schema_descriptions("en", self._schema).split(f"- {key}: ")[-1].split("\n")[0] if f"- {key}: " in get_schema_descriptions("en", self._schema) else key
                # Pick 2-3 unfilled fields to ask about
                hints = [field_labels.get(f, f) for f in all_missing[:3]]
                follow_up = ", ".join(hints)

            logger.info(
                f"Extraction agent: {completion}% complete, "
                f"missing: {missing}, next: {follow_up}"
            )

            return {
                "fields": merged,
                "missing_required": missing,
                "all_missing": all_missing,
                "completion": completion,
                "follow_up_hint": follow_up,
            }

        except Exception as e:
            logger.error(f"Extraction agent error: {e}")
            return {
                "fields": current_fields,
                "missing_required": get_missing_fields(current_fields, self._required_fields),
                "all_missing": get_all_missing_fields(current_fields, self._all_fields),
                "completion": get_completion_percentage(current_fields, self._all_fields),
                "follow_up_hint": "",
            }

    def generate_mock_lookups(
        self,
        transcript: list[dict],
        extracted_fields: dict,
    ) -> dict:
        """Scan the transcript for keywords and return mock SOP/material suggestions.

        Returns:
            dict with:
                - sop_suggestions: list of matching SOP cards (may be empty)
                - material_lookups: list of matching material cards (may be empty)
        """
        # Build a single lowercase string from all user transcript entries
        user_text = " ".join(
            entry.get("text", "").lower()
            for entry in transcript
            if entry.get("role") == "user"
        )
        # Also check extracted fields for material hints
        # Check both rawMaterials (adhesive) and ingredients (consumer brands)
        raw_materials_field = str(extracted_fields.get("rawMaterials") or extracted_fields.get("ingredients") or "").lower()
        combined = f"{user_text} {raw_materials_field}"

        # Match SOP suggestions (config-driven)
        matched_sops: list[dict] = []
        seen_sop_ids: set[str] = set()
        sop_list = self._sop_suggestions if isinstance(self._sop_suggestions, list) else SOP_SUGGESTIONS
        for sop in sop_list:
            if sop["sop_id"] in seen_sop_ids:
                continue
            for kw in sop["keywords"]:
                if kw in combined:
                    matched_sops.append({
                        "sop_id": sop["sop_id"],
                        "title": sop["title"],
                        "description": sop["description"],
                        "version": sop["version"],
                        "department": sop["department"],
                    })
                    seen_sop_ids.add(sop["sop_id"])
                    break

        # Match material lookups (config-driven)
        matched_materials: list[dict] = []
        seen_material_names: set[str] = set()
        mat_lookups = self._material_lookups if isinstance(self._material_lookups, dict) else MATERIAL_LOOKUPS
        for keyword, record in mat_lookups.items():
            if record["name"] in seen_material_names:
                continue
            if keyword in combined:
                matched_materials.append(dict(record))
                seen_material_names.add(record["name"])

        return {
            "sop_suggestions": matched_sops,
            "material_lookups": matched_materials,
        }

    async def close(self):
        """Clean up the client."""
        await self.client.close()

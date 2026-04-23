"""
LabBuddy — Extraction schema for lab experiment protocol fields.
Defines the field schema with bilingual descriptions and completion tracking.
"""

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "researcherName": {
            "type": "string",
            "description": {
                "de": "Vollständiger Name des Forschers/der Forscherin",
                "en": "Full name of the researcher"
            }
        },
        "researcherId": {
            "type": "string",
            "description": {
                "de": "Mitarbeiter-ID oder Personalnummer",
                "en": "Employee ID or personnel number"
            }
        },
        "projectName": {
            "type": "string",
            "description": {
                "de": "Name des Forschungsprojekts",
                "en": "Name of the research project"
            }
        },
        "projectCode": {
            "type": "string",
            "description": {
                "de": "Projektcode oder interne Referenznummer",
                "en": "Project code or internal reference number"
            }
        },
        "experimentTitle": {
            "type": "string",
            "description": {
                "de": "Titel des Experiments",
                "en": "Title of the experiment"
            }
        },
        "experimentType": {
            "type": "string",
            "enum": ["Formulierung", "Analytik", "Stabilitaetstest", "Prozessoptimierung", "Qualitaetskontrolle", "Sonstiges"],
            "description": {
                "de": "Art des Experiments: Formulierung, Analytik, Stabilitätstest, Prozessoptimierung, Qualitätskontrolle, Sonstiges",
                "en": "Type of experiment: Formulation, Analytics, Stability Test, Process Optimization, Quality Control, Other"
            }
        },
        "experimentDate": {
            "type": "string",
            "description": {
                "de": "Datum des Experiments (TT.MM.JJJJ)",
                "en": "Date of the experiment (DD.MM.YYYY)"
            }
        },
        "laboratory": {
            "type": "string",
            "description": {
                "de": "Bezeichnung des Labors oder Laborraums",
                "en": "Laboratory name or room designation"
            }
        },
        "equipment": {
            "type": "string",
            "description": {
                "de": "Verwendete Geräte und Instrumente (z.B. Rheometer, pH-Meter, Waage)",
                "en": "Equipment and instruments used (e.g., rheometer, pH meter, balance)"
            }
        },
        "rawMaterials": {
            "type": "string",
            "description": {
                "de": "Liste der verwendeten Rohstoffe und Chemikalien mit Chargen-/Lotnummern",
                "en": "List of raw materials and chemicals used with batch/lot numbers"
            }
        },
        "rawMaterialSource": {
            "type": "string",
            "description": {
                "de": "Herkunft/Lieferant der Rohstoffe (z.B. aus RMH-System)",
                "en": "Source/supplier of raw materials (e.g., from RMH system)"
            }
        },
        "sampleId": {
            "type": "string",
            "description": {
                "de": "Proben-ID oder Probenbezeichnung",
                "en": "Sample ID or sample designation"
            }
        },
        "batchNumber": {
            "type": "string",
            "description": {
                "de": "Chargennummer des Experiments",
                "en": "Batch number of the experiment"
            }
        },
        "targetFormulation": {
            "type": "string",
            "description": {
                "de": "Zielformulierung oder Rezeptur (Zusammensetzung in %)",
                "en": "Target formulation or recipe (composition in %)"
            }
        },
        "procedureSteps": {
            "type": "string",
            "description": {
                "de": "Durchführungsschritte des Experiments in chronologischer Reihenfolge",
                "en": "Procedure steps of the experiment in chronological order"
            }
        },
        "temperatureCelsius": {
            "type": "number",
            "description": {
                "de": "Temperatur in °C während des Experiments",
                "en": "Temperature in °C during the experiment"
            }
        },
        "humidityPercent": {
            "type": "number",
            "description": {
                "de": "Relative Luftfeuchtigkeit in % während des Experiments",
                "en": "Relative humidity in % during the experiment"
            }
        },
        "phValue": {
            "type": "number",
            "description": {
                "de": "Gemessener pH-Wert",
                "en": "Measured pH value"
            }
        },
        "viscosity": {
            "type": "string",
            "description": {
                "de": "Gemessene Viskosität (Wert und Einheit, z.B. 500 mPa·s)",
                "en": "Measured viscosity (value and unit, e.g., 500 mPa·s)"
            }
        },
        "duration": {
            "type": "string",
            "description": {
                "de": "Dauer des Experiments (z.B. 2 Stunden, 30 Minuten)",
                "en": "Duration of the experiment (e.g., 2 hours, 30 minutes)"
            }
        },
        "observations": {
            "type": "string",
            "description": {
                "de": "Beobachtungen während des Experiments (Farbe, Konsistenz, Geruch, Auffälligkeiten)",
                "en": "Observations during the experiment (color, consistency, odor, anomalies)"
            }
        },
        "result": {
            "type": "string",
            "description": {
                "de": "Ergebnis des Experiments (bestanden/nicht bestanden, Messwerte)",
                "en": "Result of the experiment (pass/fail, measurements)"
            }
        },
        "deviations": {
            "type": "string",
            "description": {
                "de": "Abweichungen vom Standard-Protokoll oder SOP",
                "en": "Deviations from standard protocol or SOP"
            }
        },
        "safetyNotes": {
            "type": "string",
            "description": {
                "de": "Sicherheitshinweise oder besondere Vorsichtsmaßnahmen",
                "en": "Safety notes or special precautions"
            }
        },
        "nextSteps": {
            "type": "string",
            "description": {
                "de": "Geplante nächste Schritte oder Folgeexperimente",
                "en": "Planned next steps or follow-up experiments"
            }
        },
        "comments": {
            "type": "string",
            "description": {
                "de": "Freitext für zusätzliche Anmerkungen",
                "en": "Free text for additional comments"
            }
        }
    },
    "required": []
}

ALL_FIELDS = list(EXTRACTION_SCHEMA["properties"].keys())

REQUIRED_FIELDS = [
    "researcherName",
    "experimentTitle",
    "experimentType",
    "experimentDate",
    "rawMaterials",
    "procedureSteps",
    "result",
]


# ── Config-driven helpers ────────────────────────────────────────────────

def build_schema_from_config(config: dict) -> dict:
    """Build an EXTRACTION_SCHEMA-compatible dict from a config's extraction_fields."""
    return {
        "type": "object",
        "properties": config["extraction_fields"],
        "required": [],
    }


def get_fields_from_config(config: dict) -> list[str]:
    """Return the list of field keys from a config."""
    return list(config["extraction_fields"].keys())


def get_required_from_config(config: dict) -> list[str]:
    """Return the required field keys from a config."""
    return list(config.get("required_fields", REQUIRED_FIELDS))


def get_field_description(field_key: str, language: str = "de", schema: dict | None = None) -> str:
    """Get the description of a field in the specified language."""
    s = schema or EXTRACTION_SCHEMA
    prop = s["properties"].get(field_key, {})
    desc = prop.get("description", {})
    if isinstance(desc, dict):
        return desc.get(language, desc.get("de", ""))
    return desc


def get_schema_descriptions(language: str = "de", schema: dict | None = None) -> str:
    """Build a schema description string in the specified language."""
    s = schema or EXTRACTION_SCHEMA
    lines = []
    for key, prop in s["properties"].items():
        desc = prop.get("description", {})
        if isinstance(desc, dict):
            text = desc.get(language, desc.get("de", ""))
        else:
            text = desc
        lines.append(f"- {key}: {text}")
    return "\n".join(lines)


def get_missing_fields(extracted: dict, required: list[str] | None = None) -> list[str]:
    """Return required fields that are still empty."""
    req = required if required is not None else REQUIRED_FIELDS
    return [f for f in req
            if not extracted.get(f) and extracted.get(f) != 0]


def get_all_missing_fields(extracted: dict, all_fields: list[str] | None = None) -> list[str]:
    """Return ALL fields that are still null or empty."""
    fields = all_fields if all_fields is not None else ALL_FIELDS
    return [f for f in fields
            if extracted.get(f) is None or extracted.get(f) == ""]


def get_completion_percentage(extracted: dict, all_fields: list[str] | None = None) -> float:
    """Percentage of all fields filled."""
    fields = all_fields if all_fields is not None else ALL_FIELDS
    if not fields:
        return 0.0
    filled = sum(1 for k in fields
                 if extracted.get(k) is not None and extracted.get(k) != "")
    return round(filled / len(fields) * 100, 1)

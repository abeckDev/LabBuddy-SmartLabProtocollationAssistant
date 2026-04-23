"""
LabBuddy — Mock data for Medium Tech Preview mode.
Centralized mock data for SOP suggestions, material lookups,
vision analysis responses, and agent activity messages.
All data is illustrative for a generic R&D lab context.
"""

from typing import Any

# ── SOP suggestions (keyword → SOP card) ─────────────────────────────────────
# Each entry lists keywords that trigger this SOP suggestion.
SOP_SUGGESTIONS: list[dict[str, Any]] = [
    {
        "keywords": [
            "viscosity", "viskosität", "brookfield", "rheometer",
            "fließverhalten", "flow", "consistency", "konsistenz",
        ],
        "sop_id": "SOP-LAB-2024-042",
        "title": "Standard Viscosity Measurement Procedure for Adhesive Formulations",
        "description": (
            "Covers Brookfield and rotational rheometer methods for adhesive "
            "viscosity characterisation at 23 °C ± 1 °C."
        ),
        "version": "3.1",
        "department": "Adhesive Technologies",
    },
    {
        "keywords": [
            "ph", "ph-wert", "ph value", "acid", "säure",
            "buffer", "puffer", "alkaline", "alkalisch",
        ],
        "sop_id": "SOP-LAB-2023-018",
        "title": "pH Measurement and Calibration Protocol for Aqueous Formulations",
        "description": (
            "Standard operating procedure for pH electrode calibration "
            "and measurement in aqueous formulations."
        ),
        "version": "2.4",
        "department": "Formulation Science",
    },
    {
        "keywords": [
            "surfactant", "tensid", "emulsion", "emulgator",
            "surface", "oberfläche", "hlb", "hlt",
        ],
        "sop_id": "SOP-LAB-2024-071",
        "title": "Surfactant Screening and HLB Value Determination",
        "description": (
            "Procedure for systematic screening of surfactant candidates "
            "including HLB determination and emulsion stability assessment."
        ),
        "version": "1.8",
        "department": "Home Care Innovation",
    },
    {
        "keywords": [
            "stability", "stabilität", "aging", "alterung",
            "shelf", "lagerung", "freeze-thaw",
        ],
        "sop_id": "SOP-LAB-2022-033",
        "title": "Accelerated Stability Testing Protocol for Consumer Products",
        "description": (
            "Protocol for accelerated ageing studies at 40 °C/75 % RH, "
            "50 °C/ambient, and freeze-thaw cycling."
        ),
        "version": "4.0",
        "department": "Quality Assurance",
    },
    {
        "keywords": [
            "formulation", "formulierung", "mixing", "mischung",
            "blend", "recipe", "rezeptur", "composition",
        ],
        "sop_id": "SOP-LAB-2024-055",
        "title": "Formulation Development and Documentation Standard",
        "description": (
            "Standard procedure for laboratory-scale formulation development, "
            "including documentation requirements for LIMS entry."
        ),
        "version": "2.2",
        "department": "R&D Core",
    },
    {
        "keywords": [
            "adhesive", "klebstoff", "bonding", "kleben",
            "bond strength", "haftung", "lap shear",
        ],
        "sop_id": "SOP-LAB-2023-089",
        "title": "Adhesive Bond Strength Testing — Lap Shear Method",
        "description": (
            "Tensile lap shear test for adhesive systems per DIN EN 1465, "
            "covering substrate preparation and conditioning."
        ),
        "version": "1.5",
        "department": "Adhesive Technologies",
    },
]

# ── Material lookups (lowercase keyword → RMH record) ─────────────────────────
MATERIAL_LOOKUPS: dict[str, dict[str, str]] = {
    "sodium lauryl sulfate": {
        "name": "Sodium Lauryl Sulfate",
        "cas": "151-21-3",
        "lot": "LAB-2024-8832",
        "supplier": "BASF",
        "grade": "Surfactant Grade",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Warehouse B, Shelf 4C",
    },
    "sls": {
        "name": "Sodium Lauryl Sulfate (SLS)",
        "cas": "151-21-3",
        "lot": "LAB-2024-8832",
        "supplier": "BASF",
        "grade": "Surfactant Grade",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Warehouse B, Shelf 4C",
    },
    "natriumlaurylsulfat": {
        "name": "Natriumlaurylsulfat (SLS)",
        "cas": "151-21-3",
        "lot": "LAB-2024-8832",
        "supplier": "BASF",
        "grade": "Tenside-Qualität",
        "spec_status": "✅ Freigegeben",
        "tds_sds": "Verfügbar",
        "location": "Lager B, Regal 4C",
    },
    "glycerin": {
        "name": "Glycerol (Glycerin)",
        "cas": "56-81-5",
        "lot": "LAB-2024-6610",
        "supplier": "Croda",
        "grade": "Cosmetic Grade (Ph.Eur.)",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Lab Cabinet 12, Bottle #3",
    },
    "glycerol": {
        "name": "Glycerol (Glycerin)",
        "cas": "56-81-5",
        "lot": "LAB-2024-6610",
        "supplier": "Croda",
        "grade": "Cosmetic Grade (Ph.Eur.)",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Lab Cabinet 12, Bottle #3",
    },
    "polyvinyl alcohol": {
        "name": "Polyvinyl Alcohol (PVA)",
        "cas": "9002-89-5",
        "lot": "LAB-2023-4417",
        "supplier": "Kuraray",
        "grade": "Poval 217S",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Warehouse A, Cold Storage",
    },
    "pva": {
        "name": "Polyvinyl Alcohol (PVA)",
        "cas": "9002-89-5",
        "lot": "LAB-2023-4417",
        "supplier": "Kuraray",
        "grade": "Poval 217S",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Warehouse A, Cold Storage",
    },
    "ethanol": {
        "name": "Ethanol (96 %)",
        "cas": "64-17-5",
        "lot": "LAB-2024-9901",
        "supplier": "Brenntag",
        "grade": "Industrial Grade",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Flammable Cabinet, Lab 302",
    },
    "propylene glycol": {
        "name": "Propylene Glycol (1,2-Propanediol)",
        "cas": "57-55-6",
        "lot": "LAB-2024-7723",
        "supplier": "Dow Chemical",
        "grade": "USP/EP Grade",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Lab Cabinet 8",
    },
    "xanthan gum": {
        "name": "Xanthan Gum",
        "cas": "11138-66-2",
        "lot": "LAB-2024-3341",
        "supplier": "CP Kelco",
        "grade": "Keltrol CG-SFT",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Dry Storage, Row 7",
    },
    "xanthan": {
        "name": "Xanthan Gum",
        "cas": "11138-66-2",
        "lot": "LAB-2024-3341",
        "supplier": "CP Kelco",
        "grade": "Keltrol CG-SFT",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Dry Storage, Row 7",
    },
    "citric acid": {
        "name": "Citric Acid Monohydrate",
        "cas": "5949-29-1",
        "lot": "LAB-2024-2208",
        "supplier": "Jungbunzlauer",
        "grade": "Food/Pharma Grade",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Lab Cabinet 3, Shelf 2",
    },
    "zitronensäure": {
        "name": "Zitronensäure Monohydrat",
        "cas": "5949-29-1",
        "lot": "LAB-2024-2208",
        "supplier": "Jungbunzlauer",
        "grade": "Lebensmittel-/Pharmaqualität",
        "spec_status": "✅ Freigegeben",
        "tds_sds": "Verfügbar",
        "location": "Laborschrank 3, Regal 2",
    },
    "carbomer": {
        "name": "Carbomer 980 (Carbopol 980)",
        "cas": "9003-01-4",
        "lot": "LAB-2024-5503",
        "supplier": "Lubrizol",
        "grade": "Carbopol 980 NF Polymer",
        "spec_status": "✅ Approved",
        "tds_sds": "Available",
        "location": "Warehouse B, Shelf 2A",
    },
}

# ── Vision analysis mock responses ────────────────────────────────────────────
VISION_RESPONSES: list[str] = [
    (
        "I can see a laboratory bench with what appears to be a rheometer and several sample "
        "containers. The rheometer is a rotational type, suitable for viscosity measurements. "
        "Multiple sample vials are visible to the right."
    ),
    (
        "The setup shows a pH meter connected to a probe immersed in a beaker solution. "
        "A temperature probe is also visible. The digital display on the meter is active."
    ),
    (
        "I observe a magnetic stirrer with a flask containing a white viscous liquid. "
        "A laboratory balance is visible to the right. The flask appears to be a 500 mL "
        "round-bottom flask."
    ),
    (
        "Lab setup includes a fume hood with several reagent bottles. Safety goggles and "
        "lab gloves are visible on the bench. A graduated cylinder and beaker are in use."
    ),
    (
        "I can see a high-shear mixer setup with a stainless steel vessel. "
        "The formulation appears to be an emulsion — white creamy texture visible. "
        "A temperature controller is attached to the vessel."
    ),
    (
        "The bench shows a UV-Vis spectrophotometer with a sample cell inserted. "
        "Reagent bottles labelled with batch codes are visible. A lab notebook is open nearby."
    ),
    (
        "I observe a centrifuge with sample tubes loaded. PPE is correctly worn. "
        "A stability testing oven set to 40 °C is visible in the background."
    ),
]

# ── Agent activity message sequence ──────────────────────────────────────────
# delay_ms is relative to when the sequence starts.
AGENT_ACTIVITY_SEQUENCES: list[dict[str, Any]] = [
    {
        "delay_ms": 0,
        "agent": "Supervisor Agent",
        "message": "New turn detected — initialising multi-agent workflow...",
        "icon": "🤖",
    },
    {
        "delay_ms": 400,
        "agent": "Documentation Agent",
        "message": "Extracting protocol fields from transcript...",
        "icon": "🔍",
    },
    {
        "delay_ms": 900,
        "agent": "SOP Compliance Agent",
        "message": "Scanning for procedure keywords to match SOPs...",
        "icon": "📚",
    },
    {
        "delay_ms": 1500,
        "agent": "Materials Agent",
        "message": "Looking up raw materials in RMH database...",
        "icon": "📦",
    },
    {
        "delay_ms": 2200,
        "agent": "Quality Agent",
        "message": "Checking field completeness and data quality...",
        "icon": "✅",
    },
    {
        "delay_ms": 2800,
        "agent": "Supervisor Agent",
        "message": "All agents completed — aggregating results.",
        "icon": "🤖",
    },
]

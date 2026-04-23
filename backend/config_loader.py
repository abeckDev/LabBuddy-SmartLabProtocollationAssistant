"""
LabBuddy — Configuration loader.
Loads demo profile configs from backend/configs/ directory.
Supports switching between different demo profiles (e.g., Adhesive Technologies vs. Consumer Brands).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIGS_DIR = Path(__file__).parent / "configs"

_config_cache: dict[str, dict] = {}


def get_default_config_name() -> str:
    """Return the default config name from DEMO_CONFIG env var, or 'adhesive_technologies'."""
    return os.getenv("DEMO_CONFIG", "adhesive_technologies")


def list_available_configs() -> list[dict[str, Any]]:
    """List all available config profiles with their names and display titles."""
    configs = []
    for path in sorted(CONFIGS_DIR.glob("*.json")):
        try:
            data = load_config(path.stem)
            configs.append({
                "name": path.stem,
                "profile_name": data.get("profile_name", {"en": path.stem, "de": path.stem}),
                "company": data.get("company", ""),
                "division": data.get("division", ""),
                "lims_name": data.get("lims", {}).get("name", ""),
            })
        except Exception as e:
            logger.warning(f"Skipping invalid config {path.name}: {e}")
    return configs


def load_config(config_name: str) -> dict:
    """Load a config by name from the configs directory. Caches after first load."""
    if config_name in _config_cache:
        return _config_cache[config_name]

    # Sanitize to prevent path traversal
    safe_name = Path(config_name).name
    config_path = CONFIGS_DIR / f"{safe_name}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Config '{safe_name}' not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _validate_config(data, safe_name)
    _config_cache[config_name] = data
    logger.info(f"Loaded config: {safe_name}")
    return data


def get_config_for_session(config_name: str | None = None) -> dict:
    """Load the specified config or fall back to the default."""
    name = config_name or get_default_config_name()
    return load_config(name)


def _validate_config(data: dict, name: str):
    """Validate that a config has all required top-level keys."""
    required_keys = [
        "profile_name", "company", "division", "lims",
        "extraction_fields", "required_fields", "field_labels",
        "lims_sections",
    ]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Config '{name}' missing required keys: {missing}")

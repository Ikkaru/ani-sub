import os
import sys
from pathlib import Path

from platformdirs import user_config_dir

# Using the tomlib package based on Python Version
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

# Directory Constant
APP_NAME = "ani-sub"
CONFIG_DIR = Path(user_config_dir(APP_NAME))
CONFIG_PATH = CONFIG_DIR / "config.toml"


# Default Configuration
DEFAULTS = {
    "engine": {"active": None, "category": None},
    "target_lang": None,
    "source_lang": "en",
    "player": "mpv"
}


# Load Function
def load() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    with CONFIG_PATH.open("rb") as f:
        data = tomllib.load(f)
    return _merge(dict(DEFAULTS), data)

# Function to throw away None before saving to toml
def _strip_none(obj):
    if isinstance(obj, dict):
        return {k: _strip_none(v) for k, v in obj.items() if v is not None}
    return obj

# Save Function
def save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Create a Temporay File
    tmp = CONFIG_PATH.with_suffix(".toml.tmp")
    with tmp.open("wb") as f:
        tomli_w.dump(_strip_none(data), f)

    # Replace Current Config with the temporary
    tmp.replace(CONFIG_PATH)
    CONFIG_PATH.chmod(0o600)


# Get Config valuee
def get(path: str, default=None):
    node = load()
    for part in path.split("."):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return default
    return node


# Set Config Values
def set_value(path: str, value) -> None:
    data = load()
    parts = path.split(".")
    node = data
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    save(data)


# Helper Function to merge 
def _merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance (base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base



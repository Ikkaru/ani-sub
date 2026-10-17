import json
from pathlib import Path
from ani_sub import langcodes

from platformdirs import user_data_dir

APP_NAME = "ani-sub"
MODEL_DIR = Path(user_data_dir(APP_NAME)) / "models"
INVENTORY_PATH = MODEL_DIR / "installed.json"


# Load Invetory 
def _load():
    if not INVENTORY_PATH.exists():
        return{}
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


# Save Inventory
def _save(data: dict):
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = INVENTORY_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(INVENTORY_PATH)


def category_of(repo: str) -> str:
    return "bilingual" if "opus-mt-" in repo else "multilingual"

def pair_from_repo(repo: str) -> str | None:
    """'Helsinki-NLP/opus-mt-en-id' -> 'en-id'; 'opus-mt-en-jap' -> 'en-ja'."""
    name = repo.split("/")[-1]
    if not name.startswith("opus-mt-"):
        return None
    src, sep, tgt = name[len("opus-mt-"):].partition("-")
    if not sep:
        return None
    return f"{langcodes.from_opus_code(src)}-{langcodes.from_opus_code(tgt)}"

def record(repo: str, sha: str, size_mb: int, category: str | None = None) -> None:
    data = _load()
    pair = pair_from_repo(repo)
    data[repo] = {
        "sha": sha,
        "size_mb": size_mb,
        "category": category or category_of(repo),
        "supports": [pair] if pair else [],   # bilingual: list pair; multilingual coming soon
    }
    _save(data)


def installed() -> dict[str, dict]:
    return _load()


def model_path(repo: str) -> Path:
    return MODEL_DIR / repo.replace("/", "__")


# Sanity Check
def is_downloaded(repo: str) -> bool:
    if repo not in _load():
        return False
    p = model_path(repo)
    return p.exists() and any(p.iterdir())


def covering(tgt: str, src: str = "en") -> list[dict]:
    result = []
    for repo, info in _load().items():
        supports = info.get("supports") or [p for p in (pair_from_repo(repo),) if p]
        if f"{src}-{tgt}" in supports:
            result.append({"repo": repo, **info})
    return result

def remove(repo: str) -> None:
    data = _load()
    data.pop(repo, None)
    _save(data)
from importlib.resources import files
import yaml


def _load() -> dict:
    ref = files("ani_sub").joinpath("registry.yaml")
    with ref.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def all_engines() -> list[dict]:
    return _load()["engines"]


def by_id(engine_id: str) -> dict | None:
    for e in all_engines():
        if e["id"] == engine_id:
            return e
    return None


def by_category(category: str) -> list[dict]:
    return [e for e in all_engines() if e["category"] == category]


def supports_pair(engine: dict, src: str, tgt: str) -> bool:
    if "*" in engine.get("support", []):
        return True
    return f"{src}-{tgt}" in engine.get("support", [])
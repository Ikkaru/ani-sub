import csv
from functools import lru_cache
from importlib.resources import files


# Load and cache csv
@lru_cache(maxsize=1)
def _load() -> dict[str, str]:
    ref = files("ani_sub").joinpath("data/language-codes.csv")
    with ref.open("r", encoding="utf-8", newline="") as f:
        return {row["alpha2"]: row["English"] for row in csv.DictReader(f)}


def validate(iso: str) -> bool:
    return iso in _load()


# Convert ISO langcodes to normal English string format
def name(iso: str, default: str = "?") -> str:
    return _load().get(iso, default)

# Conver String Format to ISO code

# List all Language
def all_languages() -> dict[str, str]:
    return dict(_load())
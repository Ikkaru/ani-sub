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
def to_name(iso: str, default: str = "?") -> str:
    return _load().get(iso, default)

# Convert String Format to ISO code
def to_code(name: str, default: str = "?") -> str:
    key = next((k for k, v in _load().items() if v == name), None)
    return key

# List all Language
def all_languages() -> dict[str, str]:
    return dict(_load())

# Opus Code Exception (Cuz Naming on Opus model is Stupid)
_OPUS_TO_ISO = {"jap": "ja", "zho": "zh", "cmn": "zh"} # zh only for protection (i think this is not needed)
_ISO_TO_OPUS = {"ja": "jap"}

# To convert non obvious opus code to ISO code
def from_opus_code(code: str) -> str:
    return _OPUS_TO_ISO.get(code, code)
# To convert from iso to opus, im find that only ja is different, will be added more if i find more
def to_opus_code(iso: str) -> str:
    return _ISO_TO_OPUS.get(iso, iso)
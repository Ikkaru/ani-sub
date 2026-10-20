from dataclasses import dataclass
from huggingface_hub import HfApi, list_models
from concurrent.futures import ThreadPoolExecutor

api = HfApi()

# Trusted Model Author on HF
TRUSTED = {"Helsinki-NLP", "facebook", "google"}

@dataclass
class ModelHit:
    repo: str
    downloads: int
    sha: str = ""
    size_mb: int = 0


def search(src: str, tgt: str) -> list[ModelHit]:
    return _search_opus(src, tgt)


# Dedicated Search Query for opus-mt model
def _search_opus(src: str, tgt: str) -> list[ModelHit]:
    from ani_sub.langcodes import to_opus_code

    opus_src = to_opus_code(src)
    opus_tgt = to_opus_code(tgt)
    suffix = f"{opus_src}-{opus_tgt}"

    hits = list_models(
        search=f"opus-mt-{suffix}",
        author= "Helsinki-NLP",
        pipeline_tag="translation",
        sort="downloads",
        limit=10
    )

    # search HF fuzzy
    return [
        ModelHit(repo=m.id, downloads=m.downloads or 0)
        for m in hits
        if m.id.split("/")[0] in TRUSTED
        and m.id.endswith(f"/opus-mt-{suffix}")
    ]


# Model Infromation
def describe(hit: ModelHit) -> ModelHit:
    info = api.model_info(hit.repo, files_metadata=True)
    hit.sha = info.sha
    hit.size_mb = sum(s.size or 0 for s in info.siblings) // 1_000_000
    return hit

def describe_all(hits: list[ModelHit], workers: int = 8) -> list[ModelHit]:
    def _safe(h):
        try:
            return describe(h)
        except Exception:
            return h
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_safe, hits))

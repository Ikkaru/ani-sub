from functools import lru_cache
from ani_sub import inventory

# For opus-mt Model
class OpusEngine:
    def __init__(self, repo: str):
        self.repo = repo
        self.model_dir = inventory.model_path(repo)
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is not None:
            return
        if not inventory.is_downloaded(self.repo):
            raise FileNotFoundError(f"{self.repo} not installed")

        from transformers import MarianMTModel, MarianTokenizer

        self._tokenizer = MarianTokenizer.from_pretrained(str(self.model_dir))
        self._model = MarianMTModel.from_pretrained(str(self.model_dir)).eval()

    def translate_batch(self, texts: list[str], batch_size: int = 16) -> list[str]:
        self._load()
        import torch

        out: list[str] = []
        with torch.inference_mode():
            # Chunking & Tokenizing
            for i in range(0, len(texts), batch_size):
                chunk = texts[i : i + batch_size]
                batch = self._tokenizer(
                    chunk,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512,
                )
                generated = self._model.generate(
                    **batch,
                    num_beams=1,
                    max_new_tokens=512,
                )
                out.extend(self._tokenizer.batch_decode(generated, skip_special_tokens=True))
            return out


@lru_cache(maxsize=1)
def get(repo: str) -> OpusEngine:
    if not inventory.is_downloaded(repo):
        raise FileNotFoundError(f"{repo} not installed — run: ani-sub config")
    return OpusEngine(repo)

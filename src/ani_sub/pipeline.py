import hashlib
import tempfile
from pathlib import Path

import httpx

from ani_sub import cache, config as cfg, engine, inventory, vtt

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def _fetch_vtt(sub_url: str, referer: str) -> str:
    resp = httpx.get(
        sub_url,
        headers={"User-Agent": UA, "Referer": referer},
        timeout=30,
        follow_redirects=True
    )
    resp.raise_for_status()
    return resp.text

def _work_base(sub_url: str) -> Path:
    stem = hashlib.sha1(sub_url.encode()).hexdigest()[:12]
    d = Path(tempfile.gettempdir()) / "ani-sub"
    d.mkdir(parents=True, exist_ok=True)
    return d / stem

def process(sub_url: str, referer: str) -> tuple[Path, Path | None]:
    # Load Config
    repo =  cfg.get("engine.active")
    src = cfg.get("source_lang") or "en"
    tgt = cfg.get("target_lang")

    # Checking model repo and target language
    if not repo or not tgt:
        raise RuntimeError("Target Language is not configured yet! run: ani-sub config")

    # Define vtt files
    base = _work_base(sub_url)
    orig_path = base.with_name(f"{base.name}_orig.vtt")
    trans_path = base.with_name(f"{base.name}_trans.vtt")

    # Fetch and write
    orig_path.write_text(_fetch_vtt(sub_url, referer), encoding="utf-8")

    # If src lang = tgt lang, no need for translation
    if src == tgt:
        return orig_path, None
    
    # Get the engine
    sha = inventory.installed().get(repo, {}).get("sha", "")
    tr = engine.get(repo)

    # Parse the subtitle
    cues = vtt.parse(str(orig_path))
    texts = [c.text for c in cues]

    # Output
    results: list[str | None] = []

    for t in texts:
        results.append(cache.get(cache.make_key(t, repo, sha, src, tgt)) if t.strip() else None) # Search in the cache

    todo = [(i, texts[i]) for i, r in enumerate(results) if r is None]
    if todo:
        translated = tr.translate_batch([t for _, t in todo], batch_size=16)
        for (i, t), out in zip(todo, translated):
            results[i] = out
            cache.store(cache.make_key(t, repo, sha, src, tgt), src, tgt, out) # Store to the cache

    # VTT out
    out_cues = [
        vtt.Cue(index=c.index, start=c.start, end=c.end, text=results[c.index] or c.text)
        for c in cues
    ]
    vtt.write(str(trans_path), out_cues)
    return orig_path, trans_path

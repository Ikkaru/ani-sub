import hashlib
import tempfile
from pathlib import Path
import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from ani_sub import cache, config as cfg, engine, inventory, vtt

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BATCH = 16

console = Console(stderr=True)

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
    with console.status("Fetching Subtitles..."):
        orig_path.write_text(_fetch_vtt(sub_url, referer), encoding="utf-8")

    # If src lang = tgt lang, no need for translation
    if src == tgt:
        return orig_path, None
    
    # Get the engine
    sha = inventory.installed().get(repo, {}).get("sha", "")
    tr = engine.get(repo)

    with console.status("Parsing subtitle..."):
        # Parse the subtitle
        cues = vtt.parse(str(orig_path))
        texts = [c.text for c in cues]

        # Output
        results: list[str | None] = [
            cache.get(cache.make_key(t, repo, sha, src, tgt)) if t.strip() else None
            for t in texts
        ]

    todo = [(i, texts[i]) for i, r in enumerate(results) if r is None]
    from_cache = len(texts) - len(todo)
    console.print(f"[dim]{from_cache} loaded from Cache, {len(todo)} will translated[/dim]")

    if todo:
        with Progress(
            SpinnerColumn(),
            TextColumn("Translating {task.completed}/{task.total} cue"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("translate", total=len(todo))
            for start in range(0, len(todo), BATCH):
                chunk = todo[start : start + BATCH]
                outs = tr.translate_batch([t for _, t in chunk], batch_size=BATCH)
                for (i, t), out in zip(chunk, outs):
                    results[i] = out
                    cache.store(cache.make_key(t, repo, sha, src, tgt), src, tgt, out)
                progress.advance(task, len(chunk))
    # VTT out
    out_cues = [
        vtt.Cue(index=c.index, start=c.start, end=c.end, text=results[c.index] or c.text)
        for c in cues
    ]
    vtt.write(str(trans_path), out_cues)
    return orig_path, trans_path

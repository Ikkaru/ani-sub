import shutil
from huggingface_hub import snapshot_download
from ani_sub import engine_search, inventory
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.console import Console
import os
os.environ["HF_HUB_VERBOSITY"] = "error"

def install(hit: engine_search.ModelHit) -> str:
    if hit.sha == "":
        engine_search.describe(hit)

    target = inventory.model_path(hit.repo)
    target.mkdir(parents=True, exist_ok=True)

    free_mb = shutil.disk_usage(target).free // 1_000_000
    if free_mb < hit.size_mb + 1000:
        raise OSError (
            f"Not enough space: need ~{hit.size_mb + 1000}MB, remaining free {free_mb}MB!"
        )

    progress_console = Console(stderr=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        transient=True
        ) as p:


        # Custom Progres Bar
        class RichProgress:
            _active_task_id = None  # Menyimpan ID task yang sedang aktif di layar

            def __init__(self, iterable=None, total=None, desc="Downloading", disable=False, *args, **kwargs):
                self.iterable = iterable
                self.desc = desc or "Downloading"
                self._total = total or 0
                self.task_id = None

                if "Downloading" not in self.desc:
                    self.disable = True
                else:
                    self.disable = disable

            def _ensure_task(self):
                if self.task_id is None and not self.disable:
                    # Hapus progress bar sebelumnya agar hanya 1 bar yang muncul di layar
                    if RichProgress._active_task_id is not None:
                        try:
                            p.remove_task(RichProgress._active_task_id)
                        except Exception:
                            pass
                    
                    self.task_id = p.add_task(
                        description=self.desc, 
                        total=self._total if self._total > 0 else None
                    )
                    RichProgress._active_task_id = self.task_id

            @property
            def format_dict(self):
                return {"rate": 0}

            @property
            def total(self):
                return self._total

            @total.setter
            def total(self, value):
                self._total = value or 0
                if self.task_id is not None:
                    try:
                        p.update(self.task_id, total=self._total)
                    except Exception:
                        pass

            def reset(self, total=None):
                if total is not None:
                    self._total = total
                if self.task_id is not None:
                    try:
                        p.reset(self.task_id, total=self._total, completed=0)
                    except Exception:
                        pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.close()
                return False

            def __iter__(self):
                if self.iterable:
                    if not self.disable:
                        self._ensure_task()
                    for item in self.iterable:
                        yield item
                        if self.task_id is not None:
                            try:
                                p.advance(self.task_id, 1)
                            except Exception:
                                pass

            def update(self, n=1):
                if n > 0 and not self.disable:
                    self._ensure_task()
                if self.task_id is not None:
                    try:
                        p.advance(self.task_id, advance=n)
                    except Exception:
                        pass

            def close(self):
                if self.task_id is not None:
                    try:
                        p.update(self.task_id, visible=False)
                        p.remove_task(self.task_id)
                    except Exception:
                        pass
                    if RichProgress._active_task_id == self.task_id:
                        RichProgress._active_task_id = None
                    self.task_id = None

            def __del__(self):
                self.close()

            def refresh(self, *args, **kwargs):
                p.refresh()

            def set_description(self, desc, refresh=True):
                self.desc = desc
                if "Downloading" not in self.desc:
                    self.disable = True
                    self.close()
                elif self.task_id is not None:
                    try:
                        p.update(self.task_id, description=desc)
                        if refresh:
                            p.refresh()
                    except Exception:
                        pass

            def set_description_str(self, desc, refresh=True):
                self.set_description(desc, refresh=refresh)

            def set_postfix_str(self, *args, **kwargs):
                pass

            def set_transfer_postfix_str(self, *args, **kwargs):
                pass


        snapshot_download(
                repo_id=hit.repo,
                revision=hit.sha,
                local_dir=target,
                tqdm_class=RichProgress
            )

    inventory.record(hit.repo, hit.sha, hit.size_mb)
    return hit.repo


def uninstall(repo: str) -> None:
    target = inventory.model_path(repo)
    if target.exists():
        shutil.rmtree(target)
    inventory.remove(repo)
    
    
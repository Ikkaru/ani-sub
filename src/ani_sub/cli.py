import typer
import questionary
from questionary import Style
from typing import Annotated
from rich.console import Console
from rich.text import Text
from importlib.metadata import version as pkg_version
from ani_sub import config as cfg
from ani_sub import colors, langcodes, inventory, engine_search, engine_downloader

console = Console()

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_enable=False,
    no_args_is_help=True
)


# Load Package Version
try:
    __version__ = pkg_version("ani-sub")
except Exception:
    __version__ = "0.0.0"


# Version Callback
def version_callback(value: bool):
    if value:
        console.print(
            f"[bold]ani-[/bold][bold {colors.PRIMARY}]sub[/bold {colors.PRIMARY}] "
            f"v[bold {colors.SECONDARY}]{__version__}[/bold {colors.SECONDARY}]"
        )
        raise typer.Exit()

    
# Program Entry Point
@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
):
    pass


# Command to Change Configuration
# Key, label, qmark, type, options

LANGS = [
    f"{code} - {names}"
    for code, names in langcodes.all_languages().items()
         ]


FIELDS = [
    ("engine.active", "Engine", "⌬", "select", None),
    ("target_lang", "Target language", "🌏︎", "autocomplete", LANGS),
    ("source_lang", "Source language", "🌏︎", "disabled", None), #PS: For now this is not required because ani-cli using default track which has english sub
    ("player", "Player", "▶", "select", [questionary.Choice(title=[("class:mpv", "mpv")], value="mpv"),
                                         questionary.Choice(title=[("class:vlc", "vlc")], value="vlc"),
                                         questionary.Choice(title=[("class:auto", "auto")], value="auto")]),
]


menu_style = Style([
            ("highlighted", f"fg:{colors.PRIMARY}"),
            ("instruction", f"fg:{colors.GREY}"),
            ("disabled", f"fg:{colors.GREY}"),
            ("active", f"fg:{colors.ACTIVE}"),
            ("download", f"fg:{colors.DARK_WHITE}"),
            ("installed", f"fg:{colors.WHITE}"),
            ("mpv", f"fg:{colors.MPV}"),
            ("vlc", f"fg:{colors.VLC}")
        ])

# Engine Selection
def _pick_model_for(src: str, tgt: str) -> str | None:
    active = cfg.get("engine.active").split("/")[-1]
    installed = inventory.covering(tgt)
    installed_repos = {m["repo"] for m in installed}


    hits = []
    try:
        with console.status("Searching for Model"):
            hits = engine_search.search(src, tgt)

            if hits:
                hits = engine_search.describe_all(hits)

        
    except Exception as e:
        console.print(f"[yellow] Failed to retrive model available for download [/yellow]")
        
    choices = []

    # Installed Model
    for m in installed:
        name = m["repo"].split("/")[-1]
        if name == active:
            choices.append(questionary.Choice(
                title=[("class:active", f"✓ {name}")],
                value=m["repo"]
            ))
        else:
            choices.append(questionary.Choice(
                title=[("class:installed", f"○ {name}")],
                value=m["repo"]
            ))

    # Model Available to Download 
    for h in hits:
        if h.repo in installed_repos:
            continue
        name = h.repo.split("/")[-1]
        size = f"{h.size_mb}MB" if h.size_mb else "?"
        choices.append(questionary.Choice(
            title=[("class:download", f"↓ {name} ({size})")],
            value=h.repo
        ))

    if not choices:
        console.print("[red] No model available for this language.")
        return None

    picked = questionary.select(
        f"Select Engine for {tgt}:",
        choices=choices,
        qmark="⌬",
        pointer=">",
        instruction="(↑/↓ to navigate, enter to select)",
        style=menu_style
    ).ask()

    if picked is None:
        return None

    if picked not in installed_repos:
        hit = next((h for h in hits if h.repo == picked), None)
        # Sanity Check
        if hit is None:
            console.print("[red]Model not found.[/red]")
            return None

        console.print(f"Model Information:\n repo\t\t: [bold cyan]{hit.repo}[/bold cyan]\n downloads\t: [bold cyan]{hit.downloads}[/bold cyan]\n size\t\t: [bold cyan]{hit.size_mb}MB[/bold cyan]")
        
        if not typer.confirm(f"Download {picked}?", default=True, abort=True):
            return None

        engine_search.describe(hit)
        engine_downloader.install(hit)

    return picked

    
@app.command()
def config():
    """Open Configuration menu """
    while True:
        choices = []
        for key, label, qmark, kind, options in FIELDS:
            current = cfg.get(key)

            # Disabled Options            
            if kind == "disabled":
                choices.append(questionary.Choice(title=f"{label}: {current or '-'}", value=key, disabled="Default"))
            else:
                choices.append(questionary.Choice(title=f"{label}: {current}", value=key))

        choices.append(questionary.Choice("Finish", value="__finish__"))
        
        picked = questionary.select(
            "ani-sub configurations",
            choices=choices,
            qmark="⚙",
            use_indicator=True,
            instruction="(↑/↓ to navigate, enter to select)",
            pointer=">",
            style=menu_style,
        ).ask(kbi_msg="\nConfiguration Saved\n")

        # Keyboard Interupt
        if picked is None or picked == "__finish__":
            break

        field = next(f for f in FIELDS if f[0] == picked)
        key, label, qmark, kind, options = field


        if kind == "select":
            if key == "engine.active":
                src = cfg.get("source_lang") or "en"
                tgt = cfg.get("target_lang")
                if not tgt:
                    console.print("[yellow]Please select source and target language first![/yellow]")
                    continue

                model = _pick_model_for(src, tgt)
                if model:
                    cfg.set_value("engine.category", inventory.category_of(model))
                    new_value = model
                else:
                    new_value = None
            else:    
                new_value = questionary.select(
                    f"{label}:",
                    choices=options,
                    pointer=">",
                    qmark=qmark,
                    instruction="(↑/↓ to navigate, enter to select)",
                    style=menu_style,
                    ).ask()
        elif kind == "autocomplete":
            typed = questionary.autocomplete(
                f"{label}:",
                choices=options,
                qmark=qmark,
                validate=lambda text: text in options,
            ).ask()

            if typed is None:
                new_value = None
            else:
                code = typed.split(" - ", 1)[0]
                model = _pick_model_for(cfg.get("source_lang") or "en", code)
                if model:
                    cfg.set_value("engine.active", model)
                    cfg.set_value("engine.category", "bilingual")
                    new_value = code
                else:
                    new_value = None
                

        else:
            current = cfg.get(key) or ""
            new_value = questionary.text(f"{label}", default=str(current)).ask()

        if new_value is not None:
            cfg.set_value(key, new_value)



# Cache Management Command
cache_app = typer.Typer(no_args_is_help=True)
app.add_typer(cache_app, name="cache")


@cache_app.command("info")
def cache_info():
    """show cache information"""
    from ani_sub import cache
    console.print(f"entry count     : {cache.count()}")
    console.print(f"size            : {cache.size()}")
    console.print(f"estimated size  : {cache.size_estimated()}")


@cache_app.command("clear")
def cache_clear():
    "clear cache"
    from ani_sub import cache
    console.print("Calculating cache...")
    if (cache.count() == 0):
        console.print(f"Cache is Empty!")
    else:
        console.print(f"Will remove {cache.size()} ({cache.size_estimated()}) of cache(s)")
        if (typer.confirm("Proceed?", default=True, abort=True)):
            try:
                if (cache.clear()):
                    console.print(f"Successfully cleared {cache.size()} ({cache.size_estimated()}) of cache(s)")
            except Exception as e:
                print(f"Something went wrong! : {e}")


if __name__  == "__main__":
    app()
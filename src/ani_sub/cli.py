import typer
import questionary
from questionary import Style
from typing import Annotated
from rich.console import Console
from rich.text import Text
from importlib.metadata import version as pkg_version
from ani_sub import config as cfg
from ani_sub import colors

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
# Key, label, type, option
# TODO: For now this is only placeholder
FIELDS = [
    ("target_lang", "Target language", "text", None),
    ("source_lang", "Source language", "text", None),
    ("player", "Player", "select", ["mpv", "vlc", "auto"]),
]


@app.command()
def config():
    """Open Configuration menu """
    while True:
        choices = []
        for key, label, _kind, *_ in FIELDS:
            current = cfg.get(key)
            choices.append(questionary.Choice(title=f"{label}: {current}", value=key))
        choices.append(questionary.Choice("Finish", value="__finish__"))
        menu_style = Style([
            ("highlighted", colors.PRIMARY),
            ("instruction", colors.GREY)
        ])
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
        key, label, kind, options = field

        if kind == "select":
            new_value = questionary.select(f"{label}:", choices=options, pointer=">").ask()
        else:
            current = cfg.get(key) or ""
            new_value = questionary.text(f"{label}", default=str(current)).ask()

        if new_value is not None:
            cfg.set_value(key, new_value)

# TODO: Create Cache Management Command
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
import typer
from typing import Annotated
from rich.console import Console
from rich.text import Text
from importlib.metadata import version as pkg_version

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
        console.print(f"[bold]ani-[/bold][bold green]sub[/bold green] v[bold cyan]{__version__}[/bold cyan]")
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

@app.command()
def settings():
    pass



if __name__  == "__main__":
    app()
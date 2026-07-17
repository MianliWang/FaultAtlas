from typing import Annotated

import typer

from faultatlas import __version__

app = typer.Typer(
    add_completion=False,
    help="Inspect the FaultAtlas foundation.",
    no_args_is_help=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback(invoke_without_command=True)
def main(
    context: typer.Context,
    version_option: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            help="Show the installed version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Run the minimal FaultAtlas command-line interface."""
    if context.invoked_subcommand is None and not version_option:
        typer.echo(context.get_help())

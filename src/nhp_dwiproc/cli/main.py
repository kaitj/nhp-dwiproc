"""Main CLI using callback pattern."""

from pathlib import Path
from types import SimpleNamespace

import typer

from nhp_dwiproc import app as app
from nhp_dwiproc.cli.commands import connectivity, index, preprocess, reconstruction

app_ = typer.Typer(
    name="NHP-DWIProc",
    add_completion=False,
    help="Diffusion MRI processing workflows.",
    pretty_exceptions_enable=False,  # Disable typer's rich-formatted traceback
)


@app_.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    # Required
    input_dir: Path = typer.Argument(
        None, exists=True, file_okay=False, readable=True, help="Input directory."
    ),
    output_dir: Path = typer.Argument(
        None, file_okay=False, writable=True, help="Output directory."
    ),
    # Options
    version: bool = typer.Option(
        False,
        "--version",
        help="Show application version and exit.",
        is_eager=True,
    ),
) -> None:
    """Diffusion MRI processing pipeline."""
    # Print version
    if version:
        info_name = ctx.info_name.replace("_", "-") if ctx.info_name else "app"
        typer.echo(f"{info_name} version: {app.version}")
        exit(0)
    if not input_dir and not output_dir or ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
    ctx.obj = SimpleNamespace(
        app=ctx.info_name,
        version=app.version,
        cfg=SimpleNamespace(
            input_dir=input_dir,
            output_dir=output_dir,
            stage=ctx.invoked_subcommand,
        ),
    )


app_.command(name="index", help="Indexing stage.")(index.command)
app_.command(name="preprocess", help="Processing stage.")(preprocess.command)
app_.command(name="reconstruction", help="Reconstruction stage.")(
    reconstruction.command
)
app_.command(name="connectivity", help="Connectivity stage.")(connectivity.command)

if __name__ == "__main__":
    app_()

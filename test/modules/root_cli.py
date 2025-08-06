import typer
from commands import template

app = typer.Typer(name="ada")
app.add_typer(template.app, name=None)

@app.callback()
def _info(ctx: typer.Context):
    """
    Ada – voice, network-security & automation assistant.
    Run `ada --help` to list sub-commands.
    """
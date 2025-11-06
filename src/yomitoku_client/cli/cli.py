import click

from .batch import batch_command
from .single import single_command


@click.group()
def cli():
    """YomiToku-Client CLI"""


cli.add_command(single_command)
cli.add_command(batch_command)


def main():
    cli()

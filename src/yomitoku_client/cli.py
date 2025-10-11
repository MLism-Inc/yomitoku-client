"""
Command Line Interface for Yomitoku Client
"""

import click
from pathlib import Path

from .client import YomitokuClient
from .exceptions import YomitokuError


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--format', '-f', 'output_format', 
              type=click.Choice(['csv', 'markdown', 'html', 'json']),
              default='csv', help='Output format')
@click.option('--output', '-o', 'output_path', 
              type=click.Path(), help='Output file path')
@click.option('--ignore-line-break', is_flag=True, 
              help='Ignore line breaks in text')
def main(input_file: str, output_format: str, output_path: str, ignore_line_break: bool):
    """
    Convert SageMaker Yomitoku API output to various formats.
    
    INPUT_FILE: Path to the JSON file from SageMaker output
    """
    try:
        client = YomitokuClient()
        
        # Process the file
        result = client.process_file(
            input_file, 
            output_format, 
            output_path,
            ignore_line_break=ignore_line_break
        )
        
        click.echo(f"Successfully converted {input_file} to {output_format}")
        if output_path:
            click.echo(f"Output saved to: {output_path}")
        else:
            click.echo("Output:")
            click.echo(result)
            
    except YomitokuError as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        exit(1)


if __name__ == '__main__':
    main()

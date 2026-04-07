"""Command-line interface for flatfile-validator.

Provides commands to validate and profile CSV/TSV files against schema rules.
"""

import json
import sys
from pathlib import Path

import click

from flatfile_validator.profiler import FileProfile
from flatfile_validator.schema import Schema, from_file as schema_from_file
from flatfile_validator.validator import Validator


@click.group()
@click.version_option()
def cli():
    """flatfile-validator: Validate and profile CSV/TSV files against schema rules."""
    pass


@cli.command("validate")
@click.argument("datafile", type=click.Path(exists=True, readable=True))
@click.option(
    "--schema",
    "-s",
    "schema_file",
    type=click.Path(exists=True, readable=True),
    required=True,
    help="Path to the JSON/YAML schema file.",
)
@click.option(
    "--delimiter",
    "-d",
    default=None,
    help="Field delimiter (default: auto-detect from file extension).",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format for validation results.",
)
@click.option(
    "--max-errors",
    default=50,
    show_default=True,
    help="Maximum number of errors to report (0 = unlimited).",
)
def validate(datafile, schema_file, delimiter, output, max_errors):
    """Validate DATAFILE against a schema definition.

    Exits with code 0 if validation passes, 1 if errors are found.
    """
    # Resolve delimiter from extension if not explicitly provided
    if delimiter is None:
        delimiter = "\t" if datafile.endswith(".tsv") else ","

    try:
        schema = schema_from_file(schema_file)
    except (ValueError, FileNotFoundError) as exc:
        click.echo(f"Error loading schema: {exc}", err=True)
        sys.exit(2)

    validator = Validator(schema, delimiter=delimiter)

    try:
        result = validator.validate_file(datafile, max_errors=max_errors or None)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error reading data file: {exc}", err=True)
        sys.exit(2)

    if output == "json":
        click.echo(
            json.dumps(
                {
                    "file": datafile,
                    "valid": result.is_valid,
                    "error_count": result.error_count,
                    "errors": [
                        {"row": e.row, "column": e.column, "message": str(e)}
                        for e in result.errors
                    ],
                },
                indent=2,
            )
        )
    else:
        status = click.style("PASSED", fg="green") if result.is_valid else click.style("FAILED", fg="red")
        click.echo(f"Validation {status} — {datafile}")
        if not result.is_valid:
            click.echo(f"  {result.error_count} error(s) found:")
            for error in result.errors:
                click.echo(f"    Row {error.row}, Column '{error.column}': {error.message}")

    sys.exit(0 if result.is_valid else 1)


@cli.command("profile")
@click.argument("datafile", type=click.Path(exists=True, readable=True))
@click.option(
    "--delimiter",
    "-d",
    default=None,
    help="Field delimiter (default: auto-detect from file extension).",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format for profile results.",
)
def profile(datafile, delimiter, output):
    """Profile DATAFILE and display column-level statistics."""
    if delimiter is None:
        delimiter = "\t" if datafile.endswith(".tsv") else ","

    try:
        file_profile = FileProfile.from_file(datafile, delimiter=delimiter)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error reading data file: {exc}", err=True)
        sys.exit(2)

    if output == "json":
        click.echo(json.dumps(file_profile.to_dict(), indent=2))
    else:
        click.echo(f"Profile — {datafile}")
        click.echo(f"  Rows : {file_profile.row_count}")
        click.echo(f"  Columns: {len(file_profile.columns)}")
        click.echo()
        for col in file_profile.columns:
            click.echo(f"  [{col.name}]")
            click.echo(f"    fill_rate  : {col.fill_rate:.1%}")
            click.echo(f"    null_rate  : {col.null_rate:.1%}")
            click.echo(f"    unique     : {col.unique_count}")
            if col.min_value is not None:
                click.echo(f"    min/max    : {col.min_value} / {col.max_value}")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()

"""Schema definition and loading for flatfile-validator.

This module provides the Schema class and related utilities for defining
and loading validation rules from YAML/JSON configuration files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Supported column data types
ColumnType = Literal["string", "integer", "float", "boolean", "date", "datetime"]


@dataclass
class ColumnSchema:
    """Validation rules for a single column."""

    name: str
    dtype: ColumnType = "string"
    required: bool = True
    nullable: bool = False
    unique: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None  # regex pattern
    date_format: Optional[str] = None  # e.g. "%Y-%m-%d"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColumnSchema":
        """Construct a ColumnSchema from a plain dictionary."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class Schema:
    """Top-level schema that describes an entire flat file."""

    name: str = "unnamed"
    delimiter: str = ","
    encoding: str = "utf-8"
    skip_rows: int = 0
    has_header: bool = True
    columns: List[ColumnSchema] = field(default_factory=list)
    allow_extra_columns: bool = False
    max_errors: int = 100  # stop collecting errors after this threshold

    # ------------------------------------------------------------------ #
    # Constructors                                                          #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Schema":
        """Build a Schema from a plain dictionary (parsed from YAML/JSON)."""
        columns_raw = data.pop("columns", [])
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        schema = cls(**filtered)
        schema.columns = [ColumnSchema.from_dict(col) for col in columns_raw]
        return schema

    @classmethod
    def from_file(cls, path: str | Path) -> "Schema":
        """Load a Schema from a YAML or JSON file.

        Args:
            path: Path to the schema configuration file.

        Returns:
            A fully constructed Schema instance.

        Raises:
            ValueError: If the file extension is unsupported or YAML is not installed.
            FileNotFoundError: If the schema file does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")

        suffix = path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            if not HAS_YAML:
                raise ValueError(
                    "PyYAML is required to load YAML schemas. "
                    "Install it with: pip install pyyaml"
                )
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        elif suffix == ".json":
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            raise ValueError(
                f"Unsupported schema file format '{suffix}'. "
                "Use .yaml, .yml, or .json."
            )

        return cls.from_dict(data)

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @property
    def column_names(self) -> List[str]:
        """Return an ordered list of expected column names."""
        return [col.name for col in self.columns]

    def get_column(self, name: str) -> Optional[ColumnSchema]:
        """Look up a ColumnSchema by name, returning None if not found."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Schema(name={self.name!r}, columns={len(self.columns)}, "
            f"delimiter={self.delimiter!r})"
        )

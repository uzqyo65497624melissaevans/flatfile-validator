"""Core validation engine for flatfile-validator.

This module provides the Validator class which applies schema rules
to parsed CSV/TSV data and collects validation errors.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

from .schema import Schema, ColumnSchema


@dataclass
class ValidationError:
    """Represents a single validation failure."""

    row: int
    column: str
    value: Any
    message: str

    def __str__(self) -> str:
        return f"Row {self.row}, Column '{self.column}': {self.message} (got {self.value!r})"


@dataclass
class ValidationResult:
    """Aggregated result of a validation run."""

    total_rows: int = 0
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return True if no validation errors were found."""
        return len(self.errors) == 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    def add_error(self, row: int, column: str, value: Any, message: str) -> None:
        self.errors.append(ValidationError(row=row, column=column, value=value, message=message))

    def summary(self) -> str:
        status = "PASSED" if self.is_valid else "FAILED"
        return (
            f"Validation {status} — "
            f"{self.total_rows} rows checked, "
            f"{self.error_count} error(s) found."
        )


class Validator:
    """Validates rows of data against a Schema definition."""

    def __init__(self, schema: Schema) -> None:
        self.schema = schema

    def validate(self, rows: List[Dict[str, str]]) -> ValidationResult:
        """Validate a list of row dicts against the schema.

        Args:
            rows: Each element is a dict mapping column name -> raw string value.

        Returns:
            A ValidationResult containing any errors found.
        """
        result = ValidationResult(total_rows=len(rows))

        for row_idx, row in enumerate(rows, start=2):  # start=2: row 1 is the header
            for col_schema in self.schema.columns:
                raw_value = row.get(col_schema.name)
                self._validate_cell(result, row_idx, col_schema, raw_value)

        return result

    # ------------------------------------------------------------------
    # Internal per-cell checks
    # ------------------------------------------------------------------

    def _validate_cell(
        self,
        result: ValidationResult,
        row: int,
        col: ColumnSchema,
        raw: Optional[str],
    ) -> None:
        """Run all applicable checks for a single cell."""

        # Missing column in row entirely
        if raw is None:
            if not col.nullable:
                result.add_error(row, col.name, raw, "Column is missing from row")
            return

        # Null / empty check
        if raw.strip() == "":
            if not col.nullable:
                result.add_error(row, col.name, raw, "Value is empty but column is not nullable")
            return  # No further type checks on empty value

        # Type coercion check
        coerced = self._coerce(raw, col.dtype)
        if coerced is None:
            result.add_error(
                row, col.name, raw,
                f"Cannot cast value to expected type '{col.dtype}'"
            )
            return

        # Min / max checks (applicable to numeric types)
        if col.min_value is not None and coerced < col.min_value:
            result.add_error(
                row, col.name, raw,
                f"Value {coerced} is below minimum {col.min_value}"
            )

        if col.max_value is not None and coerced > col.max_value:
            result.add_error(
                row, col.name, raw,
                f"Value {coerced} exceeds maximum {col.max_value}"
            )

        # Allowed values check
        if col.allowed_values and raw not in col.allowed_values:
            result.add_error(
                row, col.name, raw,
                f"Value not in allowed set: {col.allowed_values}"
            )

        # Regex pattern check
        if col.pattern and not re.fullmatch(col.pattern, raw):
            result.add_error(
                row, col.name, raw,
                f"Value does not match required pattern '{col.pattern}'"
            )

    @staticmethod
    def _coerce(value: str, dtype: str) -> Optional[Any]:
        """Attempt to coerce a raw string to the specified dtype.

        Returns the coerced value on success, or None on failure.
        """
        try:
            if dtype == "string":
                return value
            if dtype == "integer":
                return int(value)
            if dtype == "float":
                return float(value)
            if dtype == "boolean":
                if value.lower() in ("true", "1", "yes"):
                    return True
                if value.lower() in ("false", "0", "no"):
                    return False
                return None
        except (ValueError, TypeError):
            return None
        return value  # unknown dtype — pass through

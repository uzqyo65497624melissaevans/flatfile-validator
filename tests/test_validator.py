"""Tests for the flatfile_validator.validator module."""

import io
import pytest
from unittest.mock import patch, mock_open

from flatfile_validator.schema import ColumnSchema, Schema
from flatfile_validator.validator import (
    ValidationError,
    ValidationResult,
    FileValidator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_schema():
    """A minimal schema with two columns: id (int, required) and name (str)."""
    columns = [
        ColumnSchema(name="id", dtype="integer", required=True, nullable=False),
        ColumnSchema(name="name", dtype="string", required=True, nullable=True),
    ]
    return Schema(columns=columns, delimiter=",", has_header=True)


@pytest.fixture
def csv_data_valid():
    return "id,name\n1,Alice\n2,Bob\n3,Charlie\n"


@pytest.fixture
def csv_data_missing_column():
    """Row 2 is missing the 'name' column entirely (too few fields)."""
    return "id,name\n1,Alice\n2\n3,Charlie\n"


@pytest.fixture
def csv_data_bad_type():
    """Row 2 has a non-integer value in the 'id' column."""
    return "id,name\n1,Alice\nfoo,Bob\n3,Charlie\n"


@pytest.fixture
def csv_data_null_required():
    """Row 2 has an empty string for the required, non-nullable 'id' column."""
    return "id,name\n1,Alice\n,Bob\n3,Charlie\n"


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------

class TestValidationError:
    def test_str_includes_row_and_column(self):
        err = ValidationError(row=3, column="id", message="must be integer")
        text = str(err)
        assert "3" in text
        assert "id" in text
        assert "must be integer" in text

    def test_str_no_column(self):
        err = ValidationError(row=1, column=None, message="too few fields")
        text = str(err)
        assert "1" in text
        assert "too few fields" in text


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_is_valid_when_no_errors(self):
        result = ValidationResult(errors=[])
        assert result.is_valid is True
        assert result.error_count == 0

    def test_is_invalid_when_errors_present(self):
        err = ValidationError(row=1, column="id", message="bad value")
        result = ValidationResult(errors=[err])
        assert result.is_valid is False
        assert result.error_count == 1


# ---------------------------------------------------------------------------
# FileValidator — happy path
# ---------------------------------------------------------------------------

class TestFileValidatorValid:
    def test_valid_csv_returns_no_errors(self, simple_schema, csv_data_valid):
        fh = io.StringIO(csv_data_valid)
        validator = FileValidator(schema=simple_schema)
        result = validator.validate_fileobj(fh)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"


# ---------------------------------------------------------------------------
# FileValidator — type errors
# ---------------------------------------------------------------------------

class TestFileValidatorTypeErrors:
    def test_bad_integer_type_reported(self, simple_schema, csv_data_bad_type):
        fh = io.StringIO(csv_data_bad_type)
        validator = FileValidator(schema=simple_schema)
        result = validator.validate_fileobj(fh)
        assert not result.is_valid
        col_errors = [e for e in result.errors if e.column == "id"]
        assert len(col_errors) >= 1


# ---------------------------------------------------------------------------
# FileValidator — nullable / required errors
# ---------------------------------------------------------------------------

class TestFileValidatorNullableRequired:
    def test_null_in_non_nullable_required_column(self, simple_schema, csv_data_null_required):
        fh = io.StringIO(csv_data_null_required)
        validator = FileValidator(schema=simple_schema)
        result = validator.validate_fileobj(fh)
        assert not result.is_valid
        col_errors = [e for e in result.errors if e.column == "id"]
        assert len(col_errors) >= 1

    def test_null_allowed_in_nullable_column(self, simple_schema):
        # 'name' is nullable=True, so empty string should be fine
        data = "id,name\n1,\n2,Bob\n"
        fh = io.StringIO(data)
        validator = FileValidator(schema=simple_schema)
        result = validator.validate_fileobj(fh)
        assert result.is_valid, f"Unexpected errors: {result.errors}"


# ---------------------------------------------------------------------------
# FileValidator — structural errors
# ---------------------------------------------------------------------------

class TestFileValidatorStructural:
    def test_missing_required_column_in_header(self, simple_schema):
        data = "id\n1\n2\n"  # 'name' column absent from header
        fh = io.StringIO(data)
        validator = FileValidator(schema=simple_schema)
        result = validator.validate_fileobj(fh)
        assert not result.is_valid

    def test_row_with_too_few_fields(self, simple_schema, csv_data_missing_column):
        fh = io.StringIO(csv_data_missing_column)
        validator = FileValidator(schema=simple_schema)
        result = validator.validate_fileobj(fh)
        assert not result.is_valid

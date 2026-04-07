"""Tests for the schema module — ColumnSchema and Schema parsing/validation."""

import io
import json
import tempfile
import os
import pytest

from flatfile_validator.schema import ColumnSchema, Schema, from_dict as schema_from_dict, from_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_column_dict():
    return {"name": "id", "type": "integer"}


@pytest.fixture
def full_column_dict():
    return {
        "name": "email",
        "type": "string",
        "required": True,
        "nullable": False,
        "min_length": 5,
        "max_length": 255,
        "pattern": r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$",
    }


@pytest.fixture
def simple_schema_dict():
    return {
        "name": "users",
        "delimiter": ",",
        "has_header": True,
        "columns": [
            {"name": "id", "type": "integer", "required": True},
            {"name": "email", "type": "string", "required": True, "nullable": False},
            {"name": "age", "type": "integer", "required": False, "nullable": True},
            {"name": "score", "type": "float", "required": False},
        ],
    }


# ---------------------------------------------------------------------------
# ColumnSchema tests
# ---------------------------------------------------------------------------

class TestColumnSchema:
    def test_minimal_column_from_dict(self, minimal_column_dict):
        col = ColumnSchema.from_dict(minimal_column_dict)
        assert col.name == "id"
        assert col.type == "integer"
        # Defaults
        assert col.required is False
        assert col.nullable is True

    def test_full_column_from_dict(self, full_column_dict):
        col = ColumnSchema.from_dict(full_column_dict)
        assert col.name == "email"
        assert col.type == "string"
        assert col.required is True
        assert col.nullable is False
        assert col.min_length == 5
        assert col.max_length == 255
        assert col.pattern is not None

    def test_missing_name_raises(self):
        with pytest.raises((KeyError, ValueError)):
            ColumnSchema.from_dict({"type": "string"})

    def test_missing_type_raises(self):
        with pytest.raises((KeyError, ValueError)):
            ColumnSchema.from_dict({"name": "col"})

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            ColumnSchema.from_dict({"name": "col", "type": "uuid"})

    def test_allowed_types(self):
        for t in ("string", "integer", "float", "boolean", "date", "datetime"):
            col = ColumnSchema.from_dict({"name": "x", "type": t})
            assert col.type == t


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchema:
    def test_from_dict_basic(self, simple_schema_dict):
        schema = schema_from_dict(simple_schema_dict)
        assert schema.name == "users"
        assert schema.delimiter == ","
        assert schema.has_header is True
        assert len(schema.columns) == 4

    def test_column_names(self, simple_schema_dict):
        schema = schema_from_dict(simple_schema_dict)
        names = [c.name for c in schema.columns]
        assert names == ["id", "email", "age", "score"]

    def test_default_delimiter(self):
        schema = schema_from_dict({
            "columns": [{"name": "a", "type": "string"}]
        })
        assert schema.delimiter == ","

    def test_tsv_delimiter(self):
        schema = schema_from_dict({
            "delimiter": "\t",
            "columns": [{"name": "a", "type": "string"}],
        })
        assert schema.delimiter == "\t"

    def test_empty_columns_raises(self):
        with pytest.raises((ValueError, KeyError)):
            schema_from_dict({"name": "empty"})

    def test_from_file_json(self, simple_schema_dict):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(simple_schema_dict, f)
            tmp_path = f.name
        try:
            schema = from_file(tmp_path)
            assert schema.name == "users"
            assert len(schema.columns) == 4
        finally:
            os.unlink(tmp_path)

    def test_from_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            from_file("/nonexistent/path/schema.json")

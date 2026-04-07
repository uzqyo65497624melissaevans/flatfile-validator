"""Data profiling module for CSV/TSV files.

Provides statistical summaries and profile information about
columns in a flat file, useful for understanding data quality
before or after validation.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ColumnProfile:
    """Statistical profile for a single column."""

    name: str
    total_count: int = 0
    null_count: int = 0
    empty_count: int = 0
    unique_count: int = 0
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    mean_length: Optional[float] = None
    numeric_count: int = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    top_values: List[tuple] = field(default_factory=list)

    @property
    def null_rate(self) -> float:
        """Fraction of rows that are null/missing."""
        if self.total_count == 0:
            return 0.0
        return self.null_count / self.total_count

    @property
    def fill_rate(self) -> float:
        """Fraction of rows that have a non-null, non-empty value."""
        if self.total_count == 0:
            return 0.0
        return 1.0 - ((self.null_count + self.empty_count) / self.total_count)

    def to_dict(self) -> dict:
        """Serialize profile to a plain dictionary."""
        return {
            "name": self.name,
            "total_count": self.total_count,
            "null_count": self.null_count,
            "empty_count": self.empty_count,
            "unique_count": self.unique_count,
            "null_rate": round(self.null_rate, 4),
            "fill_rate": round(self.fill_rate, 4),
            "min_length": self.min_length,
            "max_length": self.max_length,
            "mean_length": round(self.mean_length, 2) if self.mean_length is not None else None,
            "numeric_count": self.numeric_count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean_value": round(self.mean_value, 4) if self.mean_value is not None else None,
            "top_values": self.top_values,
        }


@dataclass
class FileProfile:
    """Aggregate profile for an entire flat file."""

    row_count: int = 0
    column_count: int = 0
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize file profile to a plain dictionary."""
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": {name: col.to_dict() for name, col in self.columns.items()},
        }


def profile_records(records: List[dict], top_n: int = 5) -> FileProfile:
    """Build a :class:`FileProfile` from a list of row dictionaries.

    Args:
        records: Rows returned by :mod:`csv.DictReader` or equivalent.
        top_n: Number of most-frequent values to include per column.

    Returns:
        A populated :class:`FileProfile` instance.
    """
    if not records:
        return FileProfile()

    columns = list(records[0].keys())
    file_profile = FileProfile(row_count=len(records), column_count=len(columns))

    for col_name in columns:
        raw_values = [row.get(col_name) for row in records]
        col_profile = ColumnProfile(name=col_name, total_count=len(raw_values))

        lengths: List[int] = []
        numeric_values: List[float] = []
        counter: Counter = Counter()

        for val in raw_values:
            if val is None:
                col_profile.null_count += 1
                continue
            if val == "":
                col_profile.empty_count += 1
                continue

            lengths.append(len(val))
            counter[val] += 1

            try:
                numeric_values.append(float(val))
                col_profile.numeric_count += 1
            except ValueError:
                pass

        col_profile.unique_count = len(counter)
        col_profile.top_values = counter.most_common(top_n)

        if lengths:
            col_profile.min_length = min(lengths)
            col_profile.max_length = max(lengths)
            col_profile.mean_length = sum(lengths) / len(lengths)

        if numeric_values:
            col_profile.min_value = min(numeric_values)
            col_profile.max_value = max(numeric_values)
            col_profile.mean_value = sum(numeric_values) / len(numeric_values)

        file_profile.columns[col_name] = col_profile

    return file_profile

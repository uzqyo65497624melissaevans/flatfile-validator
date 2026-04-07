# flatfile-validator

A lightweight CLI tool for validating and profiling CSV/TSV files against configurable schema rules before ingestion.

---

## Installation

```bash
pip install flatfile-validator
```

Or install from source:

```bash
git clone https://github.com/yourname/flatfile-validator.git
cd flatfile-validator
pip install -e .
```

---

## Usage

Define a schema in YAML:

```yaml
# schema.yaml
delimiter: ","
columns:
  - name: id
    type: integer
    required: true
  - name: email
    type: string
    pattern: "^[\\w.+-]+@[\\w-]+\\.[a-z]{2,}$"
  - name: age
    type: integer
    min: 0
    max: 120
```

Run validation against your file:

```bash
flatfile-validator validate data.csv --schema schema.yaml
```

Generate a quick profile report:

```bash
flatfile-validator profile data.tsv --delimiter tab --output report.json
```

**Example output:**

```
✔  Rows checked : 1,042
✖  Validation errors : 3
   [row 14]  'age' value -1 is below minimum 0
   [row 87]  'email' does not match required pattern
   [row 301] 'id' is required but missing
```

---

## Options

| Flag | Description |
|------|-------------|
| `--schema` | Path to YAML schema file |
| `--delimiter` | Field delimiter (`comma`, `tab`, or custom character) |
| `--output` | Write results to a JSON or CSV report file |
| `--strict` | Exit with non-zero code on any validation error |
| `--skip-rows` | Number of header or comment rows to skip before validation |
| `--encoding` | File encoding to use when reading the input file (default: `utf-8`) |
| `--max-errors` | Stop validation after reaching this number of errors (default: unlimited) |

---

## Schema Reference

| Field | Type | Description |
|-------|------|-------------|
| `delimiter` | string | Delimiter used in the flat file (`","`, `"\t"`, etc.) |
| `columns[].name` | string | Expected column header name |
| `columns[].type` | string | Data type: `string`, `integer`, or `float` |
| `columns[].required` | boolean | Whether the field must be present and non-empty |
| `columns[].pattern` | string | Regex pattern the value must match (strings only) |
| `columns[].min` | number | Minimum allowed value (numeric types only) |
| `columns[].max` | number | Maximum allowed value (numeric types only) |

---

## License

This project is licensed under the [MIT License](LICENSE).

# Usage

Run the included sample:

```bash
python3 src/pbip_generator.py
```

That calls `create_report` and writes `output/SalesReport.pbip`.

Import a generator from `src` when you want to build your own report:

```python
import sys
sys.path.insert(0, "src")
from pbip_generator import create_report
```

- `create_report` in `pbip_generator.py` builds a one-table model.
- `create_enterprise_report` in `pbip_generator_silver.py` builds a multi-table model.
- `create_platform_report` in `pbip_generator_gold.py` builds the fuller report config.

All three write through `write_project` in `pbip_writer.py`. Call it directly for full control; its docstring describes the table and visual options. Each table can carry sample `rows`, a `csv` path read at refresh, or a calculated-table `dax` expression. With none of these it is an empty typed table to point at a real source in Desktop. Lineage tags and page and visual ids are derived from names, so regenerating a project gives a clean git diff. A visual that names an unknown field raises `ValueError` while generating.

Beyond the basics, `write_project` takes:

- `parameters=[parameter("DataSource", "Sample", choices=["Sample", "Csv"]), ...]`: Power Query parameters, written to `expressions.tmdl`. A table with both `rows` and `csv_file` switches between them on `DataSource`, reading `CsvFolder & csv_file`.
- `theme=`: a theme dict or the path to a theme `.json`, such as `templates/themes/LuxeOnyx.json`. It is registered in the report and set as the custom theme.
- Column options `description`, `isKey`, `isHidden`, `sortByColumn`, `expression` (DAX) and `m` (a Power Query `each` expression added after typing, for sort columns that DAX cannot compute without a circular dependency). Measures take a fourth item with `description` and `displayFolder`.

Visual options:

- A field given as `("Account.Name", "Account")` shows the header `Account`. Use it whenever two tables share a column name; the validator warns about repeated table headers.
- `"sort": ("Opportunity.Health Score", "asc")` sets the default sort.
- `"filters": [{"field": "Opportunity.Is Open", "values": [True]}]` adds a visual-level filter.
- `"colors": {"Won Revenue": "#C8A96A", "At Risk": "#9B3D4C"}` fixes a series colour (by measure name or label) or a category colour (by value).
- `{"type": "textbox", "text": "Sales Pipeline", "subtitle": "...", ...}` adds a page heading.

`examples/build_sales_pipeline.py` uses all of these.

Validate any project:

```bash
python3 src/validate_pbip.py output/SalesReport.pbip
python3 -m pytest tests
```

`templates/` and `examples/` do not contain configs yet.

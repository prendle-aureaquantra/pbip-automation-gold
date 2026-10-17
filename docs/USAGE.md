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

Validate any project:

```bash
python3 src/validate_pbip.py output/SalesReport.pbip
```

`templates/` and `examples/` do not contain configs yet.

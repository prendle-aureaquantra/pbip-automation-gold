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

`templates/` and `examples/` do not contain configs yet.

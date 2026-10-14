# PBIP Automation Suite

Public Power BI project generator from Aurea Quantra. It writes a `.pbip` file, a semantic model, DAX measures, and report pages that open in Power BI Desktop.

## Modules

- `src/pbip_generator.py` — one table, with cards, bar, line, and pie charts
- `src/pbip_generator_silver.py` — multiple tables, relationships, and time intelligence
- `src/pbip_generator_gold.py` — statistical measures and environment-aware report config

## Run the sample

```bash
git clone https://github.com/prendle-aureaquantra/pbip-automation-gold.git
cd pbip-automation-gold
python3 src/pbip_generator.py
```

That writes `output/SalesReport.pbip`. Open it in Power BI Desktop.

Python 3.8 or newer is enough. The generators use the standard library. `requirements.txt` lists optional packages this code does not import yet.

## Docs

- `docs/INSTALLATION.md`
- `docs/USAGE.md`

`templates/` and `examples/` are placeholders. The working sample is `python3 src/pbip_generator.py`.

## License

Copyright © 2024 Aurea Quantra. All rights reserved.

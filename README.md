# PBIP Automation Suite

Public Power BI project generator from Aurea Quantra. It writes a `.pbip` file, a semantic model, DAX measures, and report pages that open in Power BI Desktop.

## Modules

- `src/pbip_generator.py` — one table, with cards, bar, line, and pie charts
- `src/pbip_generator_silver.py` — multiple tables, relationships, and time intelligence
- `src/pbip_generator_gold.py` — statistical measures and environment-aware report config
- `src/pbip_writer.py` — the shared writer the three generators use: a TMDL semantic model and PBIR report pages
- `src/validate_pbip.py` — static checks for a PBIP folder before you open it in Desktop

## Run the sample

```bash
git clone https://github.com/prendle-aureaquantra/pbip-automation-gold.git
cd pbip-automation-gold
python3 src/pbip_generator.py
```

That writes `output/SalesReport.pbip`. Open it in Power BI Desktop.

Check a project before opening it:

```bash
python3 src/validate_pbip.py output/SalesReport.pbip examples/SalesPipeline/SalesPipeline.pbip
```

The validator checks that every field a visual uses, every column and measure named in DAX, every relationship and every sort-by column exist in the model. It also flags visuals that overlap or run off the page.Add `--schemas` to also check every report JSON file against Microsoft's published schema (needs `pip install jsonschema`, and downloads the schemas). Power BI Desktop is still the final check.

Python 3.8 or newer is enough. The generators use the standard library. `requirements.txt` lists optional packages this code does not import yet.

## Docs

- `docs/INSTALLATION.md`
- `docs/USAGE.md`

Open a checked-in project in Power BI Desktop: `examples/InvoiceRegister/InvoiceRegister.pbip` is a sample Business Central-style sales invoice register. `examples/SalesPipeline/SalesPipeline.pbip` is a sample sales pipeline with seller performance, opportunity health, and account health.

`templates/` is still a placeholder. `python3 src/pbip_generator.py` writes a separate project under `output/`.

## License

Copyright © 2024 Aurea Quantra. All rights reserved.

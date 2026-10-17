# Examples

Open either project in Power BI Desktop. The model is checked in without its data cache, so the first time you open a project every visual shows (Blank) and Desktop says some tables have incomplete or no data. Click **Refresh now** on that banner (or Home > Refresh). The sample rows are stored in the model, so the refresh needs no connection.

`InvoiceRegister/InvoiceRegister.pbip` is a sample Business Central-style sales invoice register: a Customer table, a Sales Invoice table, and one document list (document number, customer, posting date, amount). The rows are stored in the model. They are sample companies, not a live Business Central tenant.

`SalesPipeline/SalesPipeline.pbip` is a sample sales pipeline with two pages:

- **Pipeline Overview**: seller and stage slicers, KPI cards (won revenue, target attainment, open pipeline, weighted pipeline, win rate), won vs target by seller, amount by stage split into open, won and lost, pipeline by close month, and a seller performance table.
- **Deal & Account Health**: health KPIs (average score, at-risk pipeline and deals, slipped deals, accounts at risk), open pipeline by health band, a table of open opportunities with the least healthy first, and an account health table.

The report uses the Luxe Onyx theme (`templates/themes/LuxeOnyx.json`): an onyx canvas, champagne-gold accents, and Georgia titles. Won is gold, open pipeline is slate, lost and at-risk are garnet, and healthy is sage throughout.

Every number on those pages is a measure in the `Metrics` table, so slicers and cross-filtering change it. The opportunity health score is still a row-level column. It uses activity recency, stage age, close-date slippage, and whether the contact changed, and it falls into Healthy (70+), Watch (40-69) or At Risk (under 40).

Three Power Query parameters (Transform data > Edit parameters):

- `AsOfDate`: the "today" used for scores and day counts. It is 15 October 2026, so the sample does not age. Set it to the refresh date for live data.
- `DataSource`: `Sample` uses the rows stored in the model. `Csv` reads `Seller.csv`, `Account.csv`, `Opportunity.csv` and `Visit.csv` from `CsvFolder`.
- `CsvFolder`: the folder holding those files, ending in a slash. `SalesPipeline/data/` has the sample rows in that format. It is set to that folder on the machine that last built the project; `validate_pbip.py` warns when it does not exist, and `build_sales_pipeline.py --csv-folder` sets it.

`build_sales_pipeline.py` is the source for this project. It writes the model and report with `src/pbip_writer.py`, so change the measures, layout or theme there and run it again instead of editing the TMDL or PBIR files:

```bash
python3 examples/build_sales_pipeline.py
python3 examples/build_sales_pipeline.py --csv-folder D:/exports/pipeline/ --data-source Csv
```

Close the project in Desktop first: it rewrites the report and model folders. `tests/test_pbip_writer.py` fails if the checked-in files and the script's output drift apart.

The rows are sample sellers and accounts, not a live Dynamics 365 tenant.

A client report would use the same field list from their Dataverse data. Row-level security for reps and managers is the first thing to add on their tenant.

`python3 src/pbip_generator.py` writes a separate generated project under `output/`. That output is not a checked-in example.

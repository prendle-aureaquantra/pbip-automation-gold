# Examples

Open either project in Power BI Desktop.

`InvoiceRegister/InvoiceRegister.pbip` is a sample Business Central-style sales invoice register: a Customer table, a Sales Invoice table, and one document list (document number, customer, posting date, amount). The rows are stored in the model. They are sample companies, not a live Business Central tenant.

`SalesPipeline/SalesPipeline.pbip` is a sample sales pipeline: seller performance, an opportunity health score, and account health. The score uses activity recency, stage age, close-date slippage, and whether the contact changed. The as-of date is 15 October 2026, so the score does not move when the file is opened later. The rows are sample sellers and accounts, not a live Dynamics 365 tenant.

A client report would use the same field list from their Dataverse data. Row-level security for reps and managers is the first thing to add on their tenant.

`python3 src/pbip_generator.py` writes a separate generated project under `output/`. That output is not a checked-in example.

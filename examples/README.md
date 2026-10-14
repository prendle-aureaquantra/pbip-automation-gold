# Examples

Open `InvoiceRegister/InvoiceRegister.pbip` in Power BI Desktop.

This sample is shaped like a Business Central sales-invoice register: a Customer table, a Sales Invoice table, and one document list (document number, customer, posting date, amount). The rows are stored in the model. They are sample companies, not a live Business Central tenant.

A paginated report for a client would print this same field list from their Business Central APIs, for the one document they choose first.

`python3 src/pbip_generator.py` writes a separate generated project under `output/`. That output is not the checked-in example.

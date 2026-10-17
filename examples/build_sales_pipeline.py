"""
Build examples/SalesPipeline/SalesPipeline.pbip with src/pbip_writer.py.

This script is the source for the SalesPipeline example: change the model or the
report here and run it again, rather than editing the TMDL or PBIR files by hand.

    python examples/build_sales_pipeline.py
    python examples/build_sales_pipeline.py --csv-folder D:/exports/pipeline/ --data-source Csv

CsvFolder defaults to this checkout's examples/SalesPipeline/data/ folder, so the
"Csv" data source works on the machine that built the project.
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))

from pbip_writer import parameter, write_project  # noqa: E402

THEME = ROOT / "templates" / "themes" / "LuxeOnyx.json"

# Colours from the Luxe Onyx theme, for series and categories that need a fixed meaning.
GOLD, SLATE, SAGE, GARNET = "#C8A96A", "#6F7D91", "#7E9C86", "#9B3D4C"
IVORY, MUTED_GOLD = "#F2ECE1", "#A9A397"

NONE = {"summarizeBy": "none"}


def tables():
    seller = {
        "name": "Seller",
        "csv_file": "Seller.csv",
        "columns": [
            ("SellerNo", "string"),
            ("Name", "string"),
            ("RevenueTarget", "decimal", {"formatString": "$#,##0"}),
        ],
        "rows": [
            ["S01", "Jordan Hale", 80000.00],
            ["S02", "Priya Shah", 60000.00],
        ],
    }
    account = {
        "name": "Account",
        "csv_file": "Account.csv",
        "columns": [
            ("AccountNo", "string"),
            ("Name", "string"),
            ("PriorYearRevenue", "decimal", {"formatString": "$#,##0"}),
            ("LastActivityDate", "date"),
        ],
        "rows": [
            ["A01", "Sample Northwind", 42000.00, "2026-10-12"],
            ["A02", "Sample Lakeside", 18000.00, "2026-09-01"],
            ["A03", "Sample Harbor", 25000.00, "2026-10-08"],
        ],
    }
    opportunity = {
        "name": "Opportunity",
        "csv_file": "Opportunity.csv",
        "columns": [
            ("OpportunityNo", "string"),
            ("AccountNo", "string"),
            ("SellerNo", "string"),
            ("Stage", "string", {"sortByColumn": "Stage Order"}),
            ("Amount", "decimal", {"formatString": "$#,##0"}),
            ("CloseDate", "date"),
            ("OriginalCloseDate", "date"),
            ("StageEnteredDate", "date"),
            ("LastActivityDate", "date"),
            ("ContactChanged", "string"),
            ("Stage Order", "int64", {
                "isHidden": True, "formatString": "0", **NONE,
                "description": "Computed in Power Query, not DAX: a DAX sort column that reads Stage is a circular dependency.",
                "m": 'if [Stage] = "Qualify" then 1 else if [Stage] = "Propose" then 2 else if [Stage] = "Negotiate" then 3 '
                     'else if [Stage] = "Won" then 4 else if [Stage] = "Lost" then 5 else 9',
            }),
            ("Stage Age Days", "int64", {
                "formatString": "0", **NONE,
                "expression": "DATEDIFF(Opportunity[StageEnteredDate], MAX(Settings[AsOfDate]), DAY)",
            }),
            ("Slippage Days", "int64", {
                "formatString": "0", **NONE,
                "expression": "DATEDIFF(Opportunity[OriginalCloseDate], Opportunity[CloseDate], DAY)",
            }),
            ("Health Score", "int64", {
                "formatString": "0", **NONE,
                "description": "Activity recency (40), stage age (30), no close-date slippage (20) and an unchanged contact (10).",
                "expression": """
VAR AsOf = MAX(Settings[AsOfDate])
VAR ActivityDays = DATEDIFF(Opportunity[LastActivityDate], AsOf, DAY)
VAR StageDays = DATEDIFF(Opportunity[StageEnteredDate], AsOf, DAY)
VAR ActivityPts = SWITCH(TRUE(), ActivityDays <= 7, 40, ActivityDays <= 21, 20, 0)
VAR StagePts = SWITCH(TRUE(), StageDays < 14, 30, StageDays <= 30, 15, 0)
VAR SlipPts = IF(Opportunity[CloseDate] > Opportunity[OriginalCloseDate], 0, 20)
VAR ContactPts = IF(Opportunity[ContactChanged] = "Yes", 0, 10)
RETURN ActivityPts + StagePts + SlipPts + ContactPts""",
            }),
            ("Is Open", "boolean", {**NONE, "expression": 'NOT Opportunity[Stage] IN {"Won", "Lost"}'}),
            ("Stage Probability", "double", {
                "formatString": "0%", **NONE,
                "expression": 'SWITCH(Opportunity[Stage], "Qualify", 0.2, "Propose", 0.5, "Negotiate", 0.75, "Won", 1, 0)',
            }),
            ("Health Band", "string", {
                **NONE, "sortByColumn": "Health Band Order",
                "description": "Healthy is 70 or more, Watch is 40 to 69, At Risk is under 40. Won and lost deals are Closed.",
                "expression": 'IF(NOT Opportunity[Is Open], "Closed", SWITCH(TRUE(), Opportunity[Health Score] >= 70, "Healthy", '
                              'Opportunity[Health Score] >= 40, "Watch", "At Risk"))',
            }),
            ("Health Band Order", "int64", {
                "isHidden": True, "formatString": "0", **NONE,
                "description": "Built from the same inputs as Health Band, not from Health Band itself: "
                               "a sort column that reads the column it sorts is a circular dependency.",
                "expression": "IF(NOT Opportunity[Is Open], 4, SWITCH(TRUE(), Opportunity[Health Score] >= 70, 1, "
                              "Opportunity[Health Score] >= 40, 2, 3))",
            }),
        ],
        "rows": [
            ["OP-1001", "A01", "S01", "Propose", 24000.00, "2026-10-28", "2026-10-20", "2026-09-20", "2026-10-12", "No"],
            ["OP-1002", "A01", "S01", "Won", 36000.00, "2026-09-15", "2026-09-15", "2026-08-01", "2026-09-14", "No"],
            ["OP-1003", "A02", "S02", "Negotiate", 15000.00, "2026-11-15", "2026-10-01", "2026-08-01", "2026-09-02", "Yes"],
            ["OP-1004", "A02", "S02", "Lost", 9000.00, "2026-08-30", "2026-08-30", "2026-07-15", "2026-08-20", "No"],
            ["OP-1005", "A03", "S01", "Qualify", 8000.00, "2026-11-30", "2026-11-30", "2026-10-06", "2026-10-09", "No"],
            ["OP-1006", "A03", "S02", "Won", 22000.00, "2026-10-02", "2026-10-02", "2026-09-01", "2026-10-01", "No"],
        ],
    }
    visit = {
        "name": "Visit",
        "csv_file": "Visit.csv",
        "columns": [
            ("VisitNo", "string"),
            ("SellerNo", "string"),
            ("VisitDate", "date"),
            ("VisitType", "string"),
        ],
        "rows": [
            ["V01", "S01", "2026-10-01", "Discovery"],
            ["V02", "S01", "2026-10-10", "Demo"],
            ["V03", "S01", "2026-10-07", "Follow-up"],
            ["V04", "S02", "2026-09-01", "Discovery"],
            ["V05", "S02", "2026-09-28", "Demo"],
            ["V06", "S02", "2026-08-15", "Follow-up"],
        ],
    }
    calendar = {
        "name": "Calendar",
        "dataCategory": "Time",
        "columns": [
            ("Date", "date", {"isKey": True}),
            ("Year", "int64", {"formatString": "0"}),
            ("Month", "string", {"sortByColumn": "Month Key"}),
            ("Month Key", "int64", {"isHidden": True, "formatString": "0"}),
            ("Quarter", "string"),
        ],
        "dax": """
VAR FirstYear = YEAR(MIN(Opportunity[CloseDate]))
VAR LastYear = YEAR(MAX(Opportunity[CloseDate]))
RETURN
    ADDCOLUMNS(
        CALENDAR(DATE(FirstYear, 1, 1), DATE(LastYear, 12, 31)),
        "Year", YEAR([Date]),
        "Month", FORMAT([Date], "MMM yyyy"),
        "Month Key", YEAR([Date]) * 100 + MONTH([Date]),
        "Quarter", "Q" & QUARTER([Date]) & " " & YEAR([Date])
    )""",
    }
    settings = {
        "name": "Settings",
        "isHidden": True,
        "columns": [("AsOfDate", "date", {"isHidden": True})],
        "m": "#table(type table [AsOfDate = date], {{AsOfDate}})",
    }

    def folder(name):
        return {"displayFolder": name}

    metrics = {
        "name": "Metrics",
        "description": "Home for every report measure. The one column is a hidden placeholder so Desktop shows this as a measure table.",
        "columns": [("Placeholder", "string", {"isHidden": True})],
        "m": "#table(type table [Placeholder = text], {})",
        "measures": [
            ("Won Revenue", 'CALCULATE(SUM(Opportunity[Amount]), Opportunity[Stage] = "Won")', "$#,##0", folder("Revenue")),
            ("Lost Revenue", 'CALCULATE(SUM(Opportunity[Amount]), Opportunity[Stage] = "Lost")', "$#,##0", folder("Revenue")),
            ("Revenue Target", "SUM(Seller[RevenueTarget])", "$#,##0", folder("Revenue")),
            ("Revenue vs Target", "[Won Revenue] - [Revenue Target]", "$#,##0;-$#,##0", folder("Revenue")),
            ("Target Attainment", "DIVIDE([Won Revenue], [Revenue Target])", "0.0%", folder("Revenue")),
            ("Prior Year Revenue", "SUM(Account[PriorYearRevenue])", "$#,##0", folder("Revenue")),
            ("Growth vs Prior Year", "DIVIDE([Won Revenue] - [Prior Year Revenue], [Prior Year Revenue])", "0.0%", folder("Revenue")),
            ("Total Amount", "SUM(Opportunity[Amount])", "$#,##0", folder("Pipeline")),
            ("Pipeline Value", "CALCULATE(SUM(Opportunity[Amount]), Opportunity[Is Open] = TRUE())", "$#,##0", folder("Pipeline")),
            ("Won Amount", 'CALCULATE(SUM(Opportunity[Amount]), KEEPFILTERS(Opportunity[Stage] = "Won"))', "$#,##0",
             {**folder("Pipeline"), "description": "Won amount that respects a Stage filter, for visuals split by stage. "
                                                   "Won Revenue ignores the Stage filter."}),
            ("Lost Amount", 'CALCULATE(SUM(Opportunity[Amount]), KEEPFILTERS(Opportunity[Stage] = "Lost"))', "$#,##0",
             {**folder("Pipeline"), "description": "Lost amount that respects a Stage filter, for visuals split by stage."}),
            ("Weighted Pipeline", """
SUMX(
    FILTER(Opportunity, Opportunity[Is Open]),
    Opportunity[Amount] * Opportunity[Stage Probability]
)""", "$#,##0", {**folder("Pipeline"),
                 "description": "Open amount times the stage probability (Qualify 20%, Propose 50%, Negotiate 75%)."}),
            ("Opportunity Count", "COUNTROWS(Opportunity)", "0", folder("Pipeline")),
            ("Open Opportunities", "CALCULATE(COUNTROWS(Opportunity), Opportunity[Is Open] = TRUE())", "0", folder("Pipeline")),
            ("Win Rate", """
DIVIDE(
    CALCULATE(COUNTROWS(Opportunity), Opportunity[Stage] = "Won"),
    CALCULATE(COUNTROWS(Opportunity), Opportunity[Stage] IN {"Won", "Lost"})
)""", "0.0%", folder("Pipeline")),
            ("Avg Won Deal Size", 'DIVIDE([Won Revenue], CALCULATE(COUNTROWS(Opportunity), Opportunity[Stage] = "Won"))',
             "$#,##0", folder("Pipeline")),
            ("Pipeline Coverage", """
VAR Gap = [Revenue Target] - [Won Revenue]
RETURN IF(Gap > 0, DIVIDE([Pipeline Value], Gap))""", "0.00x", {
                **folder("Pipeline"),
                "description": "Open pipeline divided by the revenue still needed to hit target. Blank once target is met."}),
            ("Avg Health Score", "CALCULATE(AVERAGE(Opportunity[Health Score]), Opportunity[Is Open] = TRUE())", "0", folder("Health")),
            ("At-Risk Pipeline", 'CALCULATE([Pipeline Value], Opportunity[Health Band] = "At Risk")', "$#,##0", folder("Health")),
            ("At-Risk Deals", 'CALCULATE([Open Opportunities], Opportunity[Health Band] = "At Risk")', "0", folder("Health")),
            ("Slipped Deals", "CALCULATE([Open Opportunities], Opportunity[Slippage Days] > 0)", "0", folder("Health")),
            ("Days Since Account Activity", "DATEDIFF(MAX(Account[LastActivityDate]), MAX(Settings[AsOfDate]), DAY)", "0",
             folder("Health")),
            ("Accounts At Risk", """
VAR AsOf = MAX(Settings[AsOfDate])
RETURN
    COUNTROWS(
        FILTER(
            Account,
            [Open Opportunities] > 0
                && DATEDIFF(Account[LastActivityDate], AsOf, DAY) > 21
        )
    ) + 0""", "0", {**folder("Health"),
                    "description": "An account is at risk when it has open opportunities and no activity for more than 21 days."}),
            ("Account At Risk", 'IF(HASONEVALUE(Account[AccountNo]), IF([Accounts At Risk] > 0, "Yes", "No"))', None,
             folder("Health")),
            ("Visit Count", "COUNTROWS(Visit) + 0", "0", folder("Activity")),
            ("Days Since Last Visit", "DATEDIFF(MAX(Visit[VisitDate]), MAX(Settings[AsOfDate]), DAY)", "0", folder("Activity")),
        ],
    }
    return [metrics, seller, account, opportunity, visit, calendar, settings]


RELATIONSHIPS = [
    {"name": "OpportunitySeller", "fromTable": "Opportunity", "fromColumn": "SellerNo", "toTable": "Seller", "toColumn": "SellerNo"},
    {"name": "OpportunityAccount", "fromTable": "Opportunity", "fromColumn": "AccountNo", "toTable": "Account", "toColumn": "AccountNo"},
    {"name": "VisitSeller", "fromTable": "Visit", "fromColumn": "SellerNo", "toTable": "Seller", "toColumn": "SellerNo"},
    {"name": "OpportunityCloseDate", "fromTable": "Opportunity", "fromColumn": "CloseDate", "toTable": "Calendar", "toColumn": "Date"},
]


def header(title, subtitle):
    return {"type": "textbox", "x": 24, "y": 14, "w": 900, "h": 58, "text": title, "font": "Georgia", "size": 22,
            "color": IVORY, "subtitle": subtitle, "subtitle_size": 10, "subtitle_color": MUTED_GOLD}


def cards(measures, x0, width_total, y=84):
    gap = 8
    w = (width_total - gap * (len(measures) - 1)) // len(measures)
    out = []
    for i, m in enumerate(measures):
        x = x0 + i * (w + gap)
        last = i == len(measures) - 1
        out.append({"type": "card", "x": x, "y": y, "w": (x0 + width_total - x) if last else w, "h": 120, "measure": m})
    return out


def pages():
    overview = [
        header("Sales Pipeline", "Seller performance, open pipeline and won revenue"),
        {"type": "slicer", "x": 24, "y": 84, "w": 180, "h": 120, "title": "Seller", "category": "Seller.Name"},
        {"type": "slicer", "x": 212, "y": 84, "w": 180, "h": 120, "title": "Stage", "category": "Opportunity.Stage"},
        *cards(["Won Revenue", "Target Attainment", "Pipeline Value", "Weighted Pipeline", "Win Rate"], 404, 852),
        {"type": "clusteredBarChart", "x": 24, "y": 220, "w": 400, "h": 380, "title": "Won vs Target by Seller",
         "categories": [("Seller.Name", "Seller")], "values": ["Won Revenue", "Revenue Target"],
         "colors": {"Won Revenue": GOLD, "Revenue Target": SLATE}},
        {"type": "columnChart", "x": 436, "y": 220, "w": 400, "h": 380, "title": "Amount by Stage",
         "categories": ["Opportunity.Stage"],
         "values": [("Pipeline Value", "Open"), ("Won Amount", "Won"), ("Lost Amount", "Lost")],
         "colors": {"Open": SLATE, "Won": GOLD, "Lost": GARNET}, "sort": ("Opportunity.Stage", "asc")},
        {"type": "clusteredColumnChart", "x": 848, "y": 220, "w": 408, "h": 380, "title": "Pipeline and Won by Close Month",
         "categories": ["Calendar.Month"], "values": ["Pipeline Value", "Won Revenue"],
         "colors": {"Pipeline Value": SLATE, "Won Revenue": GOLD}, "sort": ("Calendar.Month", "asc")},
        {"type": "table", "x": 24, "y": 616, "w": 1232, "h": 204, "title": "Seller Performance",
         "values": [("Seller.Name", "Seller"), "Won Revenue", "Revenue Target", "Revenue vs Target", "Target Attainment",
                    "Pipeline Value", "Weighted Pipeline", "Pipeline Coverage", "Win Rate", "Visit Count",
                    "Days Since Last Visit"]},
    ]
    health = [
        header("Deal & Account Health", "Open deals ranked by health score, and accounts going quiet"),
        {"type": "slicer", "x": 24, "y": 84, "w": 180, "h": 120, "title": "Seller", "category": "Seller.Name"},
        *cards(["Avg Health Score", "At-Risk Pipeline", "At-Risk Deals", "Slipped Deals", "Accounts At Risk"], 212, 1044),
        {"type": "donutChart", "x": 24, "y": 220, "w": 400, "h": 380, "title": "Open Pipeline by Health Band",
         "category": "Opportunity.Health Band", "measure": "Pipeline Value",
         "colors": {"Healthy": SAGE, "Watch": GOLD, "At Risk": GARNET}},
        {"type": "table", "x": 436, "y": 220, "w": 820, "h": 380, "title": "Open Opportunity Health",
         "values": [("Opportunity.OpportunityNo", "Opportunity"), ("Account.Name", "Account"), ("Seller.Name", "Seller"),
                    "Opportunity.Stage", "Opportunity.Amount", "Opportunity.Health Score", "Opportunity.Health Band",
                    ("Opportunity.Stage Age Days", "Stage Age"), ("Opportunity.Slippage Days", "Slippage")],
         "filters": [{"field": "Opportunity.Is Open", "values": [True]}],
         "sort": ("Opportunity.Health Score", "asc")},
        {"type": "table", "x": 24, "y": 616, "w": 1232, "h": 204, "title": "Account Health",
         "values": [("Account.Name", "Account"), "Won Revenue", "Prior Year Revenue", "Growth vs Prior Year",
                    "Open Opportunities", "Pipeline Value", "Days Since Account Activity", "Account At Risk"]},
    ]
    return {"Pipeline Overview": overview, "Deal & Account Health": health}


def build(output_dir=HERE / "SalesPipeline", csv_folder=None, data_source="Sample"):
    csv_folder = csv_folder or str(HERE / "SalesPipeline" / "data")
    csv_folder = csv_folder.rstrip("\\/") + "\\"
    params = [
        parameter("AsOfDate", dt.date(2026, 10, 15),
                  "Freezes \"today\" for health scores so the sample does not age. Set it to the refresh date for live data."),
        parameter("DataSource", data_source,
                  "\"Sample\" uses the rows stored in each table. \"Csv\" reads Seller.csv, Account.csv, Opportunity.csv "
                  "and Visit.csv from CsvFolder.", choices=["Sample", "Csv"]),
        parameter("CsvFolder", csv_folder,
                  "Folder holding the CSV files, ending in a slash. Only read when DataSource is \"Csv\".", required=False),
    ]
    return write_project("SalesPipeline", tables(), RELATIONSHIPS, pages(), output_dir=output_dir,
                         page_size=(1280, 840), parameters=params, theme=THEME)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--output-dir", default=str(HERE / "SalesPipeline"))
    ap.add_argument("--csv-folder", help="folder with Seller.csv, Account.csv, Opportunity.csv and Visit.csv")
    ap.add_argument("--data-source", choices=["Sample", "Csv"], default="Sample")
    args = ap.parse_args(argv)
    print(build(args.output_dir, args.csv_folder, args.data_source))


if __name__ == "__main__":
    main()

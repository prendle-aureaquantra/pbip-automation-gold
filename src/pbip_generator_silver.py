"""
Aurora Quantra PBIP Automation Suite - Silver Tier
Semantic Model Pro - Multi-Table Models & Time Intelligence

Includes everything from Bronze, plus:
- Multi-table data models with relationships
- Time intelligence DAX (YTD, MTD, QTD, YoY, MoM, QoQ)
- Expanded visuals: matrix, slicer, treemap, waterfall, donut
- Calculated columns and hierarchies
- Solution packs for Finance, Sales, Operations

Usage:
    from pbip_generator_silver import create_enterprise_report
    create_enterprise_report("Dashboard", tables, relationships, visuals)
"""
import uuid

from pbip_writer import write_project

def guid():
    return str(uuid.uuid4())

BRAND_COLORS = {"gold": "#C4962E", "navy": "#1B365D", "green": "#4A9B4A"}

# Time Intelligence DAX Templates
TIME_INTELLIGENCE = {
    "YTD": lambda measure, date_col: f"TOTALYTD({measure}, {date_col})",
    "MTD": lambda measure, date_col: f"TOTALMTD({measure}, {date_col})",
    "QTD": lambda measure, date_col: f"TOTALQTD({measure}, {date_col})",
    "YoY": lambda measure, date_col: f"VAR Current = {measure} VAR Previous = CALCULATE({measure}, SAMEPERIODLASTYEAR({date_col})) RETURN DIVIDE(Current - Previous, Previous)",
    "MoM": lambda measure, date_col: f"VAR Current = {measure} VAR Previous = CALCULATE({measure}, DATEADD({date_col}, -1, MONTH)) RETURN DIVIDE(Current - Previous, Previous)",
    "QoQ": lambda measure, date_col: f"VAR Current = {measure} VAR Previous = CALCULATE({measure}, DATEADD({date_col}, -1, QUARTER)) RETURN DIVIDE(Current - Previous, Previous)",
    "MovingAvg30": lambda measure, date_col: f"AVERAGEX(DATESINPERIOD({date_col}, MAX({date_col}), -30, DAY), {measure})"
}

def create_enterprise_report(name, tables, relationships, visuals, output_dir="output"):
    """
    Create enterprise PBIP report with multi-table model
    
    Args:
        name: Report name
        tables: List of table configs
        relationships: List of relationship configs
        visuals: Dict of page_name -> list of visual configs
        output_dir: Output directory
    """
    pbip = write_project(name, tables, relationships, visuals, output_dir)
    print(f"Created: {pbip}")
    return pbip

def add_time_intelligence(base_measure, date_column, patterns=None):
    """Generate time intelligence measures from a base measure"""
    patterns = patterns or ["YTD", "MTD", "YoY", "MoM"]
    measures = []
    for pattern in patterns:
        if pattern in TIME_INTELLIGENCE:
            expr = TIME_INTELLIGENCE[pattern](base_measure, date_column)
            measures.append((f"{base_measure.split('[')[1].rstrip(']')} {pattern}", expr, "0.00%"))
    return measures

# Example: Sales Dashboard with Time Intelligence
if __name__ == "__main__":
    tables = [
        {
            "name": "Sales",
            "columns": [("Date", "dateTime"), ("Amount", "double"), ("CustomerID", "string"), ("Region", "string")],
            "rows": [
                ["2025-02-10", 900.0, "C1", "West"], ["2025-06-04", 1300.0, "C2", "East"],
                ["2026-01-15", 1200.0, "C1", "West"], ["2026-02-03", 860.0, "C3", "East"],
                ["2026-02-20", 1540.0, "C2", "West"], ["2026-03-11", 720.0, "C3", "Central"],
            ],
            "measures": [
                ("Total Revenue", "SUM(Sales[Amount])", "$#,##0.00"),
                ("Revenue YTD", "TOTALYTD(SUM(Sales[Amount]), Sales[Date])", "$#,##0.00"),
                ("Revenue MTD", "TOTALMTD(SUM(Sales[Amount]), Sales[Date])", "$#,##0.00"),
                ("Revenue YoY", "VAR Current = SUM(Sales[Amount]) VAR Previous = CALCULATE(SUM(Sales[Amount]), SAMEPERIODLASTYEAR(Sales[Date])) RETURN DIVIDE(Current - Previous, Previous)", "0.00%")
            ]
        },
        {
            "name": "Customers",
            "columns": [("CustomerID", "string"), ("CustomerName", "string"), ("Region", "string")],
            "rows": [["C1", "Sample Northwind", "West"], ["C2", "Sample Lakeside", "East"], ["C3", "Sample Harbor", "Central"]],
            "measures": [("Customer Count", "COUNTROWS(Customers)", "#,##0")]
        }
    ]
    
    relationships = [
        {"fromTable": "Sales", "fromColumn": "CustomerID", "toTable": "Customers", "toColumn": "CustomerID"}
    ]
    
    visuals = {
        "Overview": [
            {"x": 20, "y": 20, "w": 200, "h": 150, "type": "card", "title": "Total Revenue", "table": "Sales", "measure": "Total Revenue"},
            {"x": 240, "y": 20, "w": 200, "h": 150, "type": "card", "title": "YTD", "table": "Sales", "measure": "Revenue YTD"},
            {"x": 20, "y": 190, "w": 500, "h": 300, "type": "lineChart", "title": "Revenue Trend", "table": "Sales", "measure": "Total Revenue", "category": "Date"}
        ],
        "Time Intelligence": [
            {"x": 20, "y": 20, "w": 200, "h": 100, "type": "slicer", "title": "Region", "table": "Sales", "category": "Region"},
            {"x": 20, "y": 140, "w": 600, "h": 400, "type": "matrix", "title": "Revenue Analysis", "table": "Sales", "categories": ["Region"], "values": ["Total Revenue", "Revenue YTD", "Revenue YoY"]}
        ]
    }
    
    create_enterprise_report("SalesDashboard", tables, relationships, visuals)

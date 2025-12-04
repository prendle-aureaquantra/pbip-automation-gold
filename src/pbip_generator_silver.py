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
import os
import json
import uuid
import shutil
from pathlib import Path

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

def create_pbip_structure(name, output_dir):
    """Create PBIP folder structure"""
    output = Path(output_dir)
    report_dir = output / f"{name}.Report"
    model_dir = output / f"{name}.SemanticModel"
    
    for d in [report_dir, model_dir]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    
    with open(output / f"{name}.pbip", 'w') as f:
        json.dump({
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{name}.Report"}}],
            "settings": {"enableAutoRecovery": True}
        }, f, indent=2)
    
    return report_dir, model_dir

def create_semantic_model_multi(model_dir, name, tables, relationships):
    """Create semantic model with multiple tables and relationships"""
    with open(model_dir / "definition.pbism", 'w') as f:
        json.dump({"version": "4.0", "settings": {}}, f, indent=2)
    
    model_tables = []
    for table in tables:
        columns = [{"name": c[0], "dataType": c[1], "sourceColumn": c[0], "lineageTag": guid()} 
                   for c in table["columns"]]
        measures = [{"name": m[0], "expression": m[1], "formatString": m[2] if len(m) > 2 else "#,##0", "lineageTag": guid()} 
                    for m in table.get("measures", [])]
        
        model_tables.append({
            "name": table["name"],
            "lineageTag": guid(),
            "columns": columns,
            "measures": measures
        })
    
    model_relationships = []
    for rel in relationships:
        model_relationships.append({
            "name": rel.get("name", guid()),
            "fromTable": rel["fromTable"],
            "fromColumn": rel["fromColumn"],
            "toTable": rel["toTable"],
            "toColumn": rel["toColumn"],
            "fromCardinality": rel.get("fromCardinality", "many"),
            "toCardinality": rel.get("toCardinality", "one"),
            "crossFilteringBehavior": rel.get("crossFilteringBehavior", "bothDirections")
        })
    
    model = {
        "name": name,
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "tables": model_tables,
            "relationships": model_relationships
        }
    }
    with open(model_dir / "model.bim", 'w') as f:
        json.dump(model, f, indent=2)

def build_visual_container_silver(v, tables):
    """Build visual container supporting Silver tier visuals"""
    table = v.get("table", tables[0]["name"])
    vtype = v["type"]
    
    projections = {}
    query = None
    
    # Card
    if vtype == "card" and v.get("measure"):
        projections["Values"] = [{"queryRef": f"{table}.{v['measure']}"}]
        query = build_query(table, measures=[v["measure"]])
    
    # Charts with category
    elif vtype in ["clusteredBarChart", "lineChart", "pieChart", "areaChart", "donutChart", "treemap", "waterfallChart", "funnel"]:
        if v.get("category"):
            proj_key = "Category" if vtype not in ["treemap"] else "Group"
            projections[proj_key] = [{"queryRef": f"{table}.{v['category']}"}]
        if v.get("measure"):
            proj_key = "Values" if vtype in ["treemap"] else "Y"
            projections[proj_key] = [{"queryRef": f"{table}.{v['measure']}"}]
        
        query = build_query(table, 
                           columns=[v["category"]] if v.get("category") else [],
                           measures=[v["measure"]] if v.get("measure") else [])
    
    # Matrix
    elif vtype == "matrix":
        if v.get("categories"):
            projections["Rows"] = [{"queryRef": f"{table}.{c}"} for c in v["categories"]]
        if v.get("values"):
            projections["Values"] = [{"queryRef": f"{table}.{val}"} for val in v["values"]]
        query = build_query(table, columns=v.get("categories", []), measures=v.get("values", []))
    
    # Table
    elif vtype == "tableEx":
        if v.get("values"):
            projections["Values"] = [{"queryRef": f"{table}.{val}"} for val in v["values"]]
        query = build_query(table, columns=v.get("values", []))
    
    # Slicer
    elif vtype == "slicer" and v.get("category"):
        projections["Values"] = [{"queryRef": f"{table}.{v['category']}"}]
        query = build_query(table, columns=[v["category"]])
    
    single_visual = {
        "visualType": vtype,
        "projections": projections,
        "vcObjects": {"title": [{"properties": {"text": {"expr": {"Literal": {"Value": f"'{v['title']}'"}}}}}]}
    }
    if query:
        single_visual["prototypeQuery"] = query
    
    return {
        "x": v["x"], "y": v["y"], "width": v["w"], "height": v["h"],
        "config": json.dumps({"name": guid(), "singleVisual": single_visual}),
        "filters": "[]"
    }

def build_query(table, columns=None, measures=None):
    """Build prototype query"""
    selects = []
    for col in (columns or []):
        selects.append({"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": col}, "Name": f"{table}.{col}"})
    for msr in (measures or []):
        selects.append({"Measure": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": msr}, "Name": f"{table}.{msr}"})
    
    if not selects:
        return None
    return {"Version": 2, "From": [{"Name": "t", "Entity": table, "Type": 0}], "Select": selects}

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
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    report_dir, model_dir = create_pbip_structure(name, output_dir)
    create_semantic_model_multi(model_dir, name, tables, relationships)
    
    with open(report_dir / "definition.pbir", 'w') as f:
        json.dump({"version": "4.0", "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}}, f, indent=2)
    
    sections = []
    for idx, (page_name, page_visuals) in enumerate(visuals.items()):
        containers = [build_visual_container_silver(v, tables) for v in page_visuals]
        sections.append({
            "name": f"ReportSection{idx + 1}",
            "displayName": page_name,
            "width": 1280, "height": 720,
            "visualContainers": containers
        })
    
    with open(report_dir / "report.json", 'w') as f:
        json.dump({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
            "sections": sections
        }, f, indent=2)
    
    print(f"Created: {output / f'{name}.pbip'}")
    return output / f"{name}.pbip"

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

"""
Aurora Quantra PBIP Automation Suite - Bronze Tier
Core PBIP Generator - Basic Reports & Simple Visuals

Features:
- Programmatic PBIP file generation
- Single table data models
- Basic visuals: cards, bar charts, pie charts, line charts
- Essential DAX measures: SUM, AVERAGE, COUNT
- Opens directly in Power BI Desktop
- Save as PBIX capability

Usage:
    from pbip_generator import create_report
    create_report("MyReport", table_config, visuals)
"""
import os
import json
import uuid
import shutil
from pathlib import Path

def guid():
    return str(uuid.uuid4())

# AureaQuantra Brand Colors
BRAND_COLORS = {
    "gold": "#C4962E",
    "navy": "#1B365D",
    "green": "#4A9B4A"
}

def create_pbip_structure(name, output_dir="output"):
    """Create basic PBIP folder structure"""
    output = Path(output_dir)
    report_dir = output / f"{name}.Report"
    model_dir = output / f"{name}.SemanticModel"
    
    for d in [report_dir, model_dir]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    
    # Main .pbip file
    with open(output / f"{name}.pbip", 'w') as f:
        json.dump({
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{name}.Report"}}],
            "settings": {"enableAutoRecovery": True}
        }, f, indent=2)
    
    return report_dir, model_dir

def create_semantic_model(model_dir, name, table_config):
    """Create semantic model with single table"""
    # definition.pbism
    with open(model_dir / "definition.pbism", 'w') as f:
        json.dump({"version": "4.0", "settings": {}}, f, indent=2)
    
    # Build columns and measures
    columns = [{"name": c[0], "dataType": c[1], "sourceColumn": c[0], "lineageTag": guid()} 
               for c in table_config["columns"]]
    
    measures = []
    for m in table_config.get("measures", []):
        measures.append({
            "name": m[0],
            "expression": m[1],
            "formatString": m[2] if len(m) > 2 else "#,##0",
            "lineageTag": guid()
        })
    
    # model.bim
    model = {
        "name": name,
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "tables": [{
                "name": table_config["name"],
                "lineageTag": guid(),
                "columns": columns,
                "measures": measures
            }]
        }
    }
    with open(model_dir / "model.bim", 'w') as f:
        json.dump(model, f, indent=2)

def create_report(name, table_config, visuals, output_dir="output"):
    """
    Create a PBIP report with basic visuals
    
    Args:
        name: Report name
        table_config: Dict with name, columns, measures
        visuals: Dict of page_name -> list of visual configs
        output_dir: Output directory
    
    Returns:
        Path to created .pbip file
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    report_dir, model_dir = create_pbip_structure(name, output_dir)
    create_semantic_model(model_dir, name, table_config)
    
    # definition.pbir
    with open(report_dir / "definition.pbir", 'w') as f:
        json.dump({
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}
        }, f, indent=2)
    
    # Build pages
    sections = []
    for idx, (page_name, page_visuals) in enumerate(visuals.items()):
        containers = []
        for v in page_visuals:
            container = build_visual_container(v, table_config)
            containers.append(container)
        
        sections.append({
            "name": f"ReportSection{idx + 1}",
            "displayName": page_name,
            "width": 1280, "height": 720,
            "visualContainers": containers
        })
    
    # report.json
    with open(report_dir / "report.json", 'w') as f:
        json.dump({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
            "sections": sections
        }, f, indent=2)
    
    print(f"Created: {output / f'{name}.pbip'}")
    return output / f"{name}.pbip"

def build_visual_container(v, table_config):
    """Build a visual container for Bronze tier visuals"""
    table = table_config["name"]
    vtype = v["type"]
    
    projections = {}
    query = None
    
    if vtype == "card" and v.get("measure"):
        projections["Values"] = [{"queryRef": f"{table}.{v['measure']}"}]
        query = {
            "Version": 2,
            "From": [{"Name": "t", "Entity": table, "Type": 0}],
            "Select": [{"Measure": {"Expression": {"SourceRef": {"Source": "t"}}, 
                       "Property": v["measure"]}, "Name": f"{table}.{v['measure']}"}]
        }
    
    elif vtype in ["clusteredBarChart", "lineChart", "pieChart"]:
        if v.get("category"):
            projections["Category"] = [{"queryRef": f"{table}.{v['category']}"}]
        if v.get("measure"):
            projections["Y"] = [{"queryRef": f"{table}.{v['measure']}"}]
        
        selects = []
        if v.get("category"):
            selects.append({"Column": {"Expression": {"SourceRef": {"Source": "t"}}, 
                           "Property": v["category"]}, "Name": f"{table}.{v['category']}"})
        if v.get("measure"):
            selects.append({"Measure": {"Expression": {"SourceRef": {"Source": "t"}}, 
                           "Property": v["measure"]}, "Name": f"{table}.{v['measure']}"})
        
        if selects:
            query = {"Version": 2, "From": [{"Name": "t", "Entity": table, "Type": 0}], "Select": selects}
    
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

# Example usage
if __name__ == "__main__":
    # Define a simple sales table
    sales_table = {
        "name": "Sales",
        "columns": [
            ("Date", "dateTime"),
            ("Amount", "double"),
            ("Region", "string")
        ],
        "measures": [
            ("Total Revenue", "SUM(Sales[Amount])", "$#,##0.00"),
            ("Average Sale", "AVERAGE(Sales[Amount])", "$#,##0.00"),
            ("Count", "COUNTROWS(Sales)", "#,##0")
        ]
    }
    
    # Define visuals
    visuals = {
        "Overview": [
            {"x": 20, "y": 20, "w": 200, "h": 150, "type": "card", "title": "Total Revenue", "measure": "Total Revenue"},
            {"x": 240, "y": 20, "w": 200, "h": 150, "type": "card", "title": "Avg Sale", "measure": "Average Sale"},
            {"x": 20, "y": 190, "w": 400, "h": 300, "type": "clusteredBarChart", "title": "Revenue by Region", "measure": "Total Revenue", "category": "Region"},
            {"x": 440, "y": 190, "w": 400, "h": 300, "type": "pieChart", "title": "Distribution", "measure": "Total Revenue", "category": "Region"}
        ]
    }
    
    create_report("SalesReport", sales_table, visuals)

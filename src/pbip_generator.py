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
import uuid

from pbip_writer import write_project

def guid():
    return str(uuid.uuid4())

# AureaQuantra Brand Colors
BRAND_COLORS = {
    "gold": "#C4962E",
    "navy": "#1B365D",
    "green": "#4A9B4A"
}

def create_report(name, table_config, visuals, output_dir="output"):
    """
    Create a PBIP report with basic visuals
    
    Args:
        name: Report name
        table_config: Dict with name, columns, measures, and optional rows or csv
        visuals: Dict of page_name -> list of visual configs
        output_dir: Output directory
    
    Returns:
        Path to created .pbip file
    """
    pbip = write_project(name, [table_config], [], visuals, output_dir)
    print(f"Created: {pbip}")
    return pbip

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
        "rows": [
            ["2026-01-15", 1200.0, "West"],
            ["2026-02-03", 860.0, "East"],
            ["2026-02-20", 1540.0, "West"],
            ["2026-03-11", 720.0, "Central"],
            ["2026-03-28", 990.0, "East"],
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

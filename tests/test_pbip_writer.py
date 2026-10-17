import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "examples"))

from pbip_writer import FieldResolver, parameter, write_project  # noqa: E402
from validate_pbip import validate  # noqa: E402

TABLES = [
    {"name": "Metrics", "columns": [("Placeholder", "string", {"isHidden": True})],
     "m": "#table(type table [Placeholder = text], {})",
     "measures": [("Total", "SUM(Deal[Amount])", "$#,##0", {"displayFolder": "Sales", "description": "All deals."})]},
    {"name": "Account", "columns": [("AccountNo", "string"), ("Name", "string")], "rows": [["A1", "Acme"]]},
    {"name": "Seller", "columns": [("SellerNo", "string"), ("Name", "string")], "rows": [["S1", "Sam"]]},
    {"name": "Deal", "csv_file": "Deal.csv",
     "columns": [("AccountNo", "string"), ("SellerNo", "string"), ("Stage", "string", {"sortByColumn": "Stage Order"}),
                 ("Amount", "decimal"), ("Is Open", "boolean", {"expression": 'Deal[Stage] <> "Won"'}),
                 ("Stage Order", "int64", {"isHidden": True, "m": 'if [Stage] = "Won" then 2 else 1'})],
     "rows": [["A1", "S1", "Open", 10.0], ["A1", "S1", "Won", 20.0]]},
]
RELS = [
    {"fromTable": "Deal", "fromColumn": "AccountNo", "toTable": "Account", "toColumn": "AccountNo"},
    {"fromTable": "Deal", "fromColumn": "SellerNo", "toTable": "Seller", "toColumn": "SellerNo"},
]


def build(tmp_path, visuals, **kw):
    params = kw.pop("parameters", [parameter("DataSource", "Sample", choices=["Sample", "Csv"]),
                                   parameter("CsvFolder", str(tmp_path) + "\\", required=False)])
    pbip = write_project("T", TABLES, RELS, {"Page": visuals}, output_dir=tmp_path, parameters=params, **kw)
    return pbip


def visuals_of(pbip):
    root = Path(pbip).parent / "T.Report" / "definition" / "pages"
    return [json.loads(p.read_text()) for p in sorted(root.glob("*/visuals/*/visual.json"))]


def test_labels_become_display_names(tmp_path):
    pbip = build(tmp_path, [{"type": "table", "x": 0, "y": 0, "w": 400, "h": 200,
                             "values": [("Account.Name", "Account"), ("Seller.Name", "Seller"), "Total"]}])
    proj = visuals_of(pbip)[0]["visual"]["query"]["queryState"]["Values"]["projections"]
    assert [p.get("displayName") for p in proj] == ["Account", "Seller", None]
    errors, warnings = validate(pbip)
    assert errors == [] and warnings == []


def test_validator_warns_on_duplicate_headers(tmp_path):
    pbip = build(tmp_path, [{"type": "table", "x": 0, "y": 0, "w": 400, "h": 200,
                             "values": ["Account.Name", "Seller.Name"]}])
    errors, warnings = validate(pbip)
    assert errors == []
    assert any("share the header 'Name'" in w for w in warnings)


def test_native_query_refs_are_unique(tmp_path):
    # Desktop fails the whole visual when two fields share a nativeQueryRef, labels or not.
    pbip = build(tmp_path, [{"type": "table", "x": 0, "y": 0, "w": 400, "h": 200,
                             "values": ["Account.Name", "Seller.Name", ("Deal.Stage", "Name")]}])
    proj = visuals_of(pbip)[0]["visual"]["query"]["queryState"]["Values"]["projections"]
    natives = [p["nativeQueryRef"] for p in proj]
    assert len(set(natives)) == 3


def test_validator_errors_on_shared_native_query_ref(tmp_path):
    pbip = build(tmp_path, [{"type": "table", "x": 0, "y": 0, "w": 400, "h": 200,
                             "values": [("Account.Name", "Account"), ("Seller.Name", "Seller")]}])
    vjson = next((Path(pbip).parent / "T.Report").rglob("visual.json"))
    doc = json.loads(vjson.read_text())
    for p in doc["visual"]["query"]["queryState"]["Values"]["projections"]:
        p["nativeQueryRef"] = "Name"
    vjson.write_text(json.dumps(doc))
    errors, _ = validate(pbip)
    assert any("share nativeQueryRef 'Name'" in e for e in errors)


def test_sort_filter_and_colors(tmp_path):
    pbip = build(tmp_path, [
        {"type": "columnChart", "x": 0, "y": 0, "w": 400, "h": 200, "categories": ["Deal.Stage"],
         "values": [("Total", "All")], "colors": {"All": "#C8A96A"}, "sort": ("Deal.Stage", "asc")},
        {"type": "donutChart", "x": 0, "y": 210, "w": 400, "h": 200, "category": "Deal.Stage", "measure": "Total",
         "colors": {"Won": "#7E9C86"}, "filters": [{"field": "Deal.Is Open", "values": [True]}]},
    ])
    chart, donut = sorted(visuals_of(pbip), key=lambda v: v["position"]["y"])
    sort = chart["visual"]["query"]["sortDefinition"]["sort"][0]
    assert sort["direction"] == "Ascending" and sort["field"]["Column"]["Property"] == "Stage"
    assert chart["visual"]["objects"]["dataPoint"][0]["selector"] == {"metadata": "Metrics.Total"}
    comparison = donut["visual"]["objects"]["dataPoint"][0]["selector"]["data"][0]["scopeId"]["Comparison"]
    assert comparison["Right"] == {"Literal": {"Value": "'Won'"}}
    flt = donut["filterConfig"]["filters"][0]["filter"]["Where"][0]["Condition"]["In"]
    assert flt["Values"] == [[{"Literal": {"Value": "true"}}]]
    assert validate(pbip)[0] == []


def test_unknown_color_key_raises(tmp_path):
    with pytest.raises(ValueError, match="color key"):
        build(tmp_path, [{"type": "card", "x": 0, "y": 0, "w": 100, "h": 100, "measure": "Total", "colors": {"Nope": "#000000"}}])


def test_csv_switch_and_power_query_columns(tmp_path):
    pbip = build(tmp_path, [])
    tmdl = (Path(pbip).parent / "T.SemanticModel" / "definition" / "tables" / "Deal.tmdl").read_text()
    assert 'if DataSource = "Csv" then' in tmdl and 'CsvFolder & "Deal.csv"' in tmdl
    assert '#"Add Stage Order" = Table.AddColumn(Typed, "Stage Order"' in tmdl
    # Power Query columns are not in the sample rows or the typed column list
    assert '{"Stage Order", Int64.Type}' not in tmdl
    metrics = (Path(pbip).parent / "T.SemanticModel" / "definition" / "tables" / "Metrics.tmdl").read_text()
    assert "/// All deals." in metrics and "displayFolder: Sales" in metrics


def test_parameters_and_missing_csv_folder(tmp_path):
    missing = str(tmp_path / "nope") + "\\"
    pbip = build(tmp_path, [], parameters=[parameter("DataSource", "Sample", choices=["Sample", "Csv"]),
                                           parameter("CsvFolder", missing, required=False)])
    errors, warnings = validate(pbip)
    assert errors == [] and any("CsvFolder" in w for w in warnings)
    pbip = build(tmp_path, [], parameters=[parameter("DataSource", "Csv", choices=["Sample", "Csv"]),
                                           parameter("CsvFolder", missing, required=False)])
    errors, _ = validate(pbip)
    assert any("refresh will fail" in e for e in errors)


def test_theme_is_registered(tmp_path):
    pbip = build(tmp_path, [], theme={"name": "Test Theme", "dataColors": ["#000000"]})
    report_dir = Path(pbip).parent / "T.Report"
    report = json.loads((report_dir / "definition" / "report.json").read_text())
    assert report["themeCollection"]["customTheme"]["name"] == "TestTheme.json"
    assert (report_dir / "StaticResources" / "RegisteredResources" / "TestTheme.json").is_file()
    assert validate(pbip)[0] == []
    (report_dir / "StaticResources" / "RegisteredResources" / "TestTheme.json").unlink()
    assert any("has no file" in e for e in validate(pbip)[0])


def test_field_resolver_rejects_ambiguous_names():
    resolve = FieldResolver(TABLES)
    assert resolve("Account.Name", "Metrics") == ("Column", "Account", "Name")
    with pytest.raises(ValueError, match="ambiguous"):
        resolve("Name", "Metrics")


@pytest.mark.parametrize("example", ["SalesPipeline/SalesPipeline.pbip", "InvoiceRegister/InvoiceRegister.pbip"])
def test_checked_in_examples_validate(example):
    errors, _ = validate(ROOT / "examples" / example)
    assert errors == []


def test_sales_pipeline_build_matches_checked_in(tmp_path):
    """The checked-in SalesPipeline is the output of examples/build_sales_pipeline.py."""
    import build_sales_pipeline

    checked_in = ROOT / "examples" / "SalesPipeline"
    csv_folder = None
    for line in (checked_in / "SalesPipeline.SemanticModel" / "definition" / "expressions.tmdl").read_text().splitlines():
        if line.startswith("expression CsvFolder"):
            csv_folder = line.split('"')[1]
    build_sales_pipeline.build(tmp_path, csv_folder=csv_folder)
    for f in sorted(p for p in tmp_path.rglob("*") if p.is_file()):
        rel = f.relative_to(tmp_path)
        assert (checked_in / rel).read_bytes() == f.read_bytes(), f"{rel} differs; rerun examples/build_sales_pipeline.py"

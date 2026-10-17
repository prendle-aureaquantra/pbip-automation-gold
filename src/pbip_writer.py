"""
Shared PBIP writer: TMDL semantic model + PBIR report, the format Power BI Desktop
opens from a folder (the same layout as the projects under examples/).

The tier generators call `write_project`. You can also call it directly:

    from pbip_writer import write_project
    write_project(
        "MyReport",
        tables=[{
            "name": "Sales",
            "columns": [("Date", "dateTime"), ("Amount", "decimal", {"formatString": "$#,##0"}), ("Region", "string")],
            "measures": [("Total Revenue", "SUM(Sales[Amount])", "$#,##0")],
            "rows": [["2026-01-05", 1200, "West"]],      # or "csv": "C:/data/sales.csv", or neither
        }],
        relationships=[],
        pages={"Overview": [
            {"x": 20, "y": 20, "w": 200, "h": 120, "type": "card", "title": "Revenue", "measure": "Total Revenue"},
            {"x": 240, "y": 20, "w": 400, "h": 300, "type": "clusteredBarChart", "title": "By Region",
             "category": "Region", "measure": "Total Revenue"},
        ]},
    )

Table sources, per table:
- "rows": sample rows stored in the model (dates as "YYYY-MM-DD" strings or date objects)
- "csv": a CSV file path read at refresh
- "dax": a calculated table expression
- none of these: an empty typed table, to be pointed at a real source in Desktop

Visual fields: "measure", "category", "categories", "values", "x_axis", "y_axis",
"size", or a generic "fields": {"Role": ["Field", ...]}. A field name resolves to a
measure first, then to a column of the visual's "table", then of any table.
"Table.Column" picks a table explicitly. An unknown field raises ValueError.
"""
import datetime as _dt
import json
import re
import shutil
import uuid
from pathlib import Path

_NS = uuid.UUID("6f1c2a9e-4b7d-4f0a-9c3e-2d5b8a7e1f40")

M_TYPES = {
    "string": "type text",
    "int64": "Int64.Type",
    "double": "type number",
    "decimal": "type number",
    "dateTime": "type datetime",
    "date": "type date",
    "boolean": "type logical",
}

# Legacy type names used by the tier generators -> PBIR visual types and their roles
VISUAL_TYPES = {"matrix": "pivotTable", "table": "tableEx"}
CATEGORY_ROLE = {"treemap": "Group"}
VALUE_ROLE = {"treemap": "Values", "card": "Values", "slicer": "Values", "tableEx": "Values", "pivotTable": "Values"}

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"


def stable_id(*parts, hex20=False):
    """Deterministic id, so regenerating a project gives a clean git diff."""
    u = uuid.uuid5(_NS, "/".join(str(p) for p in parts))
    return u.hex[:20] if hex20 else str(u)


def quote(name):
    return name if re.fullmatch(r"[A-Za-z_]\w*", name) else "'" + name.replace("'", "''") + "'"


def _expr(expr, indent):
    """Single-line expressions stay inline; multi-line ones become an indented block."""
    expr = expr.strip()
    if "\n" not in expr:
        return f" = {expr}"
    pad = "\t" * indent
    return " =\n" + "\n".join(pad + line for line in expr.splitlines())


def _m_literal(value, data_type):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if data_type in ("dateTime", "date"):
        if isinstance(value, str):
            value = _dt.datetime.fromisoformat(value)
        if isinstance(value, _dt.datetime) and (value.hour or value.minute or value.second):
            return f"#datetime({value.year}, {value.month}, {value.day}, {value.hour}, {value.minute}, {value.second})"
        return f"#date({value.year}, {value.month}, {value.day})"
    if isinstance(value, (int, float)):
        return repr(value)
    return '"' + str(value).replace('"', '""') + '"'


def _m_field(name):
    return name if re.fullmatch(r"[A-Za-z_]\w*", name) else '#"' + name.replace('"', '""') + '"'


def _norm_columns(table):
    cols = []
    for c in table.get("columns", []):
        name, dtype = c[0], c[1]
        props = dict(c[2]) if len(c) > 2 else {}
        cols.append((name, dtype, props))
    return cols


def _partition_source(table, cols):
    names = "{" + ", ".join(f'"{n}"' for n, _, p in cols if "expression" not in p) + "}"
    types = ",\n".join(f'\t\t\t\t\t\t{{"{n}", {M_TYPES.get(t, "type any")}}}' for n, t, p in cols if "expression" not in p)
    if "rows" in table:
        data_cols = [(n, t) for n, t, p in cols if "expression" not in p]
        rows = ",\n".join(
            "\t\t\t\t\t\t{" + ", ".join(_m_literal(v, t) for v, (_, t) in zip(r, data_cols)) + "}"
            for r in table["rows"]
        )
        source = f"Table.FromRows(\n\t\t\t\t\t{{\n{rows}\n\t\t\t\t\t}},\n\t\t\t\t\t{names}\n\t\t\t\t)"
    elif "csv" in table:
        path = str(table["csv"]).replace('"', '""')
        source = (f'Table.PromoteHeaders(Csv.Document(File.Contents("{path}"), '
                  f'[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]), [PromoteAllScalars = true])')
    else:
        fields = ", ".join(_m_field(n) + " = " + M_TYPES.get(t, "type any").replace("type ", "")
                           for n, t, p in cols if "expression" not in p)
        return f" #table(type table [{fields}], {{}})"
    return (
        "\n\t\t\tlet\n"
        f"\t\t\t\tSource = {source},\n"
        f"\t\t\t\tTyped = Table.TransformColumnTypes(\n\t\t\t\t\tSource,\n\t\t\t\t\t{{\n{types}\n\t\t\t\t\t}},\n\t\t\t\t\t\"en-US\"\n\t\t\t\t)\n"
        "\t\t\tin\n\t\t\t\tTyped"
    )


def table_tmdl(model_name, table):
    tname = table["name"]
    cols = _norm_columns(table)
    out = [f"table {quote(tname)}", f"\tlineageTag: {stable_id(model_name, tname)}", ""]
    for m in table.get("measures", []):
        mname, expr = m[0], m[1]
        fmt = m[2] if len(m) > 2 else "#,##0"
        out.append(f"\tmeasure {quote(mname)}{_expr(expr, 3)}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tlineageTag: {stable_id(model_name, tname, 'measure', mname)}")
        out.append("")
    calculated = "dax" in table
    for name, dtype, props in cols:
        expr = props.get("expression")
        out.append(f"\tcolumn {quote(name)}{_expr(expr, 3) if expr else ''}")
        out.append(f"\t\tdataType: {'dateTime' if dtype == 'date' else dtype}")
        if props.get("isHidden"):
            out.append("\t\tisHidden")
        fmt = props.get("formatString") or ("yyyy-MM-dd" if dtype in ("date", "dateTime") else None)
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tlineageTag: {stable_id(model_name, tname, 'column', name)}")
        numeric = dtype in ("int64", "double", "decimal")
        out.append(f"\t\tsummarizeBy: {props.get('summarizeBy', 'sum' if numeric and not calculated else 'none')}")
        if calculated and not expr:
            out.append("\t\tisNameInferred")
            out.append(f"\t\tsourceColumn: [{name}]")
        elif not expr:
            out.append(f"\t\tsourceColumn: {name}")
        if props.get("sortByColumn"):
            out.append(f"\t\tsortByColumn: {quote(props['sortByColumn'])}")
        out.append("")
    if calculated:
        body = "\n".join("\t\t\t\t" + line for line in table["dax"].strip().splitlines())
        out.append(f"\tpartition {quote(tname)} = calculated\n\t\tmode: import\n\t\tsource = ```\n{body}\n\t\t\t\t```")
    else:
        out.append(f"\tpartition {quote(tname)} = m\n\t\tmode: import\n\t\tsource ={_partition_source(table, cols)}")
    out += ["", "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(out)


class FieldResolver:
    def __init__(self, tables):
        self.measures = {}
        self.columns = {}
        for t in tables:
            for m in t.get("measures", []):
                self.measures[m[0]] = t["name"]
            for c in t.get("columns", []):
                self.columns.setdefault(t["name"], set()).add(c[0])

    def __call__(self, field, default_table):
        if field in self.measures:
            return "Measure", self.measures[field], field
        if "." in field:
            t, c = field.split(".", 1)
            if c in self.columns.get(t, ()):
                return "Column", t, c
            if self.measures.get(c) == t:
                return "Measure", t, c
        if field in self.columns.get(default_table, ()):
            return "Column", default_table, field
        owners = [t for t, cols in self.columns.items() if field in cols]
        if len(owners) == 1:
            return "Column", owners[0], field
        raise ValueError(f"visual field {field!r} is not a measure or a column of {default_table}"
                         + (f" (ambiguous between {owners})" if owners else ""))


def _roles(v, vtype):
    if "fields" in v:
        return dict(v["fields"])
    cat_role = CATEGORY_ROLE.get(vtype, "Category")
    val_role = VALUE_ROLE.get(vtype, "Y")
    roles = {}
    if vtype == "slicer":
        roles["Values"] = [v["category"]] if v.get("category") else v.get("values", [])
    elif vtype == "pivotTable":
        roles["Rows"] = v.get("categories", [])
        roles["Values"] = v.get("values", [])
    elif vtype == "tableEx":
        roles["Values"] = v.get("values", [])
    elif vtype == "scatterChart":
        for key, role in (("category", "Category"), ("x_axis", "X"), ("y_axis", "Y"), ("size", "Size")):
            if v.get(key):
                roles[role] = [v[key]]
    else:
        cats = v.get("categories") or ([v["category"]] if v.get("category") else [])
        vals = v.get("values") or ([v["measure"]] if v.get("measure") else [])
        if cats and vtype != "card":
            roles[cat_role] = cats
        if vals:
            roles[val_role] = vals
    return {r: f for r, f in roles.items() if f}


def visual_json(v, name, z, resolve, default_table):
    vtype = VISUAL_TYPES.get(v["type"], v["type"])
    state = {}
    for role, fields in _roles(v, vtype).items():
        projections = []
        for f in fields:
            kind, ent, prop = resolve(f, v.get("table", default_table))
            projections.append({
                "field": {kind: {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}},
                "queryRef": f"{ent}.{prop}",
                "nativeQueryRef": prop,
            })
        state[role] = {"projections": projections}
    visual = {"visualType": vtype, "query": {"queryState": state}}
    if v.get("title") and vtype != "card":
        visual["visualContainerObjects"] = {"title": [{"properties": {
            "show": {"expr": {"Literal": {"Value": "true"}}},
            "text": {"expr": {"Literal": {"Value": "'" + v["title"].replace("'", "''") + "'"}}},
        }}]}
    return {
        "$schema": SCHEMA + "item/report/definition/visualContainer/2.0.0/schema.json",
        "name": name,
        "position": {"x": v["x"], "y": v["y"], "z": z, "height": v["h"], "width": v["w"], "tabOrder": z},
        "visual": visual,
    }


def _dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def write_project(name, tables, relationships=(), pages=None, output_dir="output",
                  page_size=(1280, 720), display_name=None):
    """Write `<output_dir>/<name>.pbip` with a TMDL model and PBIR report. Returns the .pbip path."""
    output = Path(output_dir)
    report_dir, model_dir = output / f"{name}.Report", output / f"{name}.SemanticModel"
    for d in (report_dir, model_dir):
        if d.exists():
            shutil.rmtree(d)
    output.mkdir(parents=True, exist_ok=True)
    resolve = FieldResolver(tables)
    default_table = tables[0]["name"] if tables else None

    _dump(output / f"{name}.pbip", {
        "version": "1.0", "artifacts": [{"report": {"path": f"{name}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })

    # --- semantic model ---
    _dump(model_dir / ".platform", {
        "$schema": SCHEMA + "gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": name},
        "config": {"version": "2.0", "logicalId": stable_id(name, "model")},
    })
    _dump(model_dir / "definition.pbism", {"version": "4.1", "settings": {}})
    d = model_dir / "definition"
    (d / "tables").mkdir(parents=True)
    (d / "cultures").mkdir()
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1601\n")
    (d / "cultures" / "en-US.tmdl").write_text("cultureInfo en-US\n")
    (d / "model.tmdl").write_text(
        f"model {quote(name)}\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\n"
        + "".join(f"ref table {quote(t['name'])}\n" for t in tables)
        + "\nref cultureInfo en-US\n")
    for t in tables:
        (d / "tables" / f"{t['name']}.tmdl").write_text(table_tmdl(name, t), encoding="utf-8")
    if relationships:
        rels = []
        for r in relationships:
            rid = r.get("name") or stable_id(name, "rel", r["fromTable"], r["fromColumn"], r["toTable"], r["toColumn"])
            lines = [f"relationship {quote(rid)}"]
            if r.get("crossFilteringBehavior") == "bothDirections":
                lines.append("\tcrossFilteringBehavior: bothDirections")
            lines.append(f"\tfromColumn: {quote(r['fromTable'])}.{quote(r['fromColumn'])}")
            lines.append(f"\ttoColumn: {quote(r['toTable'])}.{quote(r['toColumn'])}")
            rels.append("\n".join(lines))
        (d / "relationships.tmdl").write_text("\n\n".join(rels) + "\n")

    # --- report ---
    _dump(report_dir / ".platform", {
        "$schema": SCHEMA + "gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": display_name or name},
        "config": {"version": "2.0", "logicalId": stable_id(name, "report")},
    })
    _dump(report_dir / "definition.pbir", {
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}},
    })
    rd = report_dir / "definition"
    # themeCollection is required by the schema; empty means Desktop's default theme.
    _dump(rd / "report.json", {"$schema": SCHEMA + "item/report/definition/report/1.3.0/schema.json",
                               "layoutOptimization": "None", "themeCollection": {}})
    _dump(rd / "version.json", {"$schema": SCHEMA + "item/report/definition/versionMetadata/1.0.0/schema.json",
                                "version": "2.0.0"})
    _dump(rd / "bookmarks" / "bookmarks.json", {
        "$schema": SCHEMA + "item/report/definition/bookmarksMetadata/1.0.0/schema.json", "items": []})
    page_ids = []
    width, height = page_size
    for page_name, visuals in (pages or {}).items():
        pid = stable_id(name, "page", page_name, hex20=True)
        page_ids.append(pid)
        _dump(rd / "pages" / pid / "page.json", {
            "$schema": SCHEMA + "item/report/definition/page/1.4.0/schema.json",
            "name": pid, "displayName": page_name, "displayOption": "FitToPage",
            "height": height, "width": width,
        })
        for i, v in enumerate(visuals):
            vid = stable_id(name, "visual", page_name, i, hex20=True)
            _dump(rd / "pages" / pid / "visuals" / vid / "visual.json",
                  visual_json(v, vid, (i + 1) * 1000, resolve, default_table))
    _dump(rd / "pages" / "pages.json", {
        "$schema": SCHEMA + "item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": page_ids, **({"activePageName": page_ids[0]} if page_ids else {}),
    })
    return output / f"{name}.pbip"

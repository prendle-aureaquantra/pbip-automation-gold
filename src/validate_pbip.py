"""
Static checks for a PBIP project (TMDL semantic model + PBIR report).

Power BI Desktop is the only full validator, and it runs on Windows. This catches
the mistakes that most often stop a project from opening: broken JSON, visuals
that point at fields the model does not have, DAX that names a missing column or
measure, relationships or sort columns that do not resolve, and duplicate names.

Usage:
    python3 src/validate_pbip.py examples/SalesPipeline/SalesPipeline.pbip [more.pbip ...]
    python3 src/validate_pbip.py --schemas examples/SalesPipeline/SalesPipeline.pbip

--schemas also validates every report JSON file against the Microsoft schema named
in its "$schema". It downloads those schemas and needs `pip install jsonschema`.

Exit code is 1 when any error is found.
"""
import json
import re
import sys
from pathlib import Path


def _name(raw):
    raw = raw.strip()
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    return raw


class Table:
    def __init__(self, name):
        self.name = name
        self.columns = {}   # name -> {"expr": str|None, "props": dict}
        self.measures = {}  # name -> expr
        self.partitions = []  # (kind, source)
        self.calculated = False


class Model:
    def __init__(self):
        self.tables = {}
        self.relationships = []  # (name, from, to)
        self.expressions = set()
        self.expression_values = {}  # name -> M text after "="
        self.refs = []
        self.lineage = []


# --- TMDL ------------------------------------------------------------------

_OBJ = re.compile(r"^(\t*)(table|column|measure|partition|expression|relationship|hierarchy|level|annotation|ref table|ref cultureInfo|ref expression)\s+(.*)$")


def _split_decl(rest):
    """`'My Name' = expr` -> ('My Name', 'expr'); `Name` -> ('Name', None)."""
    m = re.match(r"^('(?:[^']|'')*'|[^=\s]+)\s*(?:=\s*(.*))?$", rest)
    if not m:
        return _name(rest), None
    return _name(m.group(1)), m.group(2)


def _read_block(lines, i, depth):
    """Collect continuation lines deeper than `depth` (multi-line expressions)."""
    out = []
    in_fence = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip("\t"))
        if stripped.startswith("```"):
            in_fence = not in_fence
            i += 1
            if not in_fence:
                break
            continue
        if not in_fence and stripped and indent <= depth + 1:
            break
        if not in_fence and re.match(r"^\t*\w[\w ]*:\s", line) and indent == depth + 1:
            break
        out.append(stripped)
        i += 1
    return "\n".join(out), i


def parse_tmdl(definition, errors):
    model = Model()
    files = sorted(definition.rglob("*.tmdl"))
    for f in files:
        lines = f.read_text(encoding="utf-8").splitlines()
        table = None
        obj = None
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("///") or not line.strip():
                i += 1
                continue
            m = _OBJ.match(line)
            if m:
                depth, kind, rest = len(m.group(1)), m.group(2), m.group(3)
                if kind == "table" and depth == 0:
                    name, _ = _split_decl(rest)
                    table = model.tables.setdefault(name, Table(name))
                    obj = ("table", table)
                elif kind in ("column", "measure") and table is not None:
                    name, expr = _split_decl(rest)
                    if expr == "":
                        expr, i = _read_block(lines, i + 1, depth)
                        i -= 1
                    if kind == "column":
                        if name in table.columns:
                            errors.append(f"{f.name}: duplicate column {table.name}[{name}]")
                        table.columns[name] = {"expr": expr, "props": {}}
                        obj = ("column", table.columns[name])
                    else:
                        if name in table.measures:
                            errors.append(f"{f.name}: duplicate measure [{name}]")
                        table.measures[name] = expr
                        obj = ("measure", None)
                elif kind == "partition" and table is not None:
                    pname, ptype = _split_decl(rest)
                    table.calculated |= (ptype or "").strip() == "calculated"
                    obj = ("partition", table)
                    # the source follows as `source =` / `source = ...`
                    j = i + 1
                    src = ""
                    while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip("\t")) > depth):
                        s = lines[j].strip()
                        if s.startswith("source ="):
                            first = s[len("source ="):].strip()
                            body, j = _read_block(lines, j + 1, depth + 1)
                            src = (first + "\n" + body).strip()
                            break
                        j += 1
                    table.partitions.append(((ptype or "").strip(), src))
                elif kind == "expression":
                    name, value = _split_decl(rest)
                    model.expressions.add(name)
                    model.expression_values[name] = value or ""
                    obj = ("expression", None)
                elif kind == "relationship":
                    rel = {"name": _name(rest)}
                    model.relationships.append(rel)
                    obj = ("relationship", rel)
                elif kind == "ref table":
                    model.refs.append(_name(rest))
                else:
                    obj = (kind, None)
                i += 1
                continue
            prop = re.match(r"^\t+(\w+)(?::\s*(.*))?$", line)
            if prop and obj:
                key, val = prop.group(1), prop.group(2)
                if key == "lineageTag":
                    model.lineage.append((val, f.name))
                if obj[0] == "relationship" and key in ("fromColumn", "toColumn"):
                    obj[1][key] = val
                if obj[0] == "column":
                    obj[1]["props"][key] = val
            i += 1
    return model


def _split_ref(ref):
    """`Opportunity.CloseDate` or `'My Table'.'My Col'` -> (table, column)."""
    m = re.match(r"^('(?:[^']|'')*'|[^.]+)\.(.+)$", ref)
    return (_name(m.group(1)), _name(m.group(2))) if m else (None, None)


def _strip_strings(dax):
    return re.sub(r'"(?:[^"]|"")*"', '""', dax)


def _m_string(value):
    m = re.match(r'^\s*"((?:[^"]|"")*)"', value or "")
    return m.group(1).replace('""', '"') if m else None


def check_csv_folder(model, errors, warnings):
    """A CsvFolder that does not exist fails the refresh once DataSource is "Csv"."""
    folder = _m_string(model.expression_values.get("CsvFolder"))
    if folder is None or Path(folder).is_dir():
        return
    message = f"parameter CsvFolder is {folder}, which does not exist on this machine"
    if _m_string(model.expression_values.get("DataSource")) == "Csv":
        errors.append(message + " and DataSource is Csv, so refresh will fail")
    else:
        warnings.append(message + " (only read when DataSource is Csv)")


def check_model(model, errors, warnings=None):
    warnings = [] if warnings is None else warnings
    all_measures = {m: t.name for t in model.tables.values() for m in t.measures}

    for name in model.refs:
        if name not in model.tables:
            errors.append(f"model.tmdl: `ref table {name}` has no table file")
    for name in model.tables:
        if model.refs and name not in model.refs:
            errors.append(f"model.tmdl: table {name} is not listed with `ref table`")

    seen = {}
    for tag, where in model.lineage:
        if tag in seen:
            errors.append(f"lineageTag {tag} is used in both {seen[tag]} and {where}")
        seen[tag] = where

    for rel in model.relationships:
        for end in ("fromColumn", "toColumn"):
            t, c = _split_ref(rel.get(end, ""))
            if t not in model.tables or c not in model.tables[t].columns:
                errors.append(f"relationship {rel['name']}: {end} {rel.get(end)} does not exist")

    for t in model.tables.values():
        for cname, col in t.columns.items():
            sort = col["props"].get("sortByColumn")
            if sort and _name(sort) not in t.columns:
                errors.append(f"{t.name}[{cname}]: sortByColumn {sort} does not exist")
        for kind, src in t.partitions:
            if kind == "m":
                for param in ("DataSource", "CsvFolder", "AsOfDate"):
                    if re.search(rf"\b{param}\b", _strip_strings(src)) and param not in model.expressions:
                        errors.append(f"{t.name}: partition uses parameter {param}, which is not defined")

    check_csv_folder(model, errors, warnings)

    # DAX references in measures, calculated columns and calculated tables
    def check_dax(owner, dax, local_cols=()):
        if not dax:
            return
        text = _strip_strings(dax)
        for tref, cref in re.findall(r"('(?:[^']|'')+'|\b[A-Za-z_]\w*)\[([^\]]+)\]", text):
            tname = _name(tref)
            if tname not in model.tables:
                errors.append(f"{owner}: DAX names table {tname}, which does not exist")
            elif cref not in model.tables[tname].columns and cref not in model.tables[tname].measures:
                errors.append(f"{owner}: DAX names {tname}[{cref}], which does not exist")
        for bare in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", text):
            if bare not in all_measures and bare not in local_cols:
                errors.append(f"{owner}: DAX names measure [{bare}], which does not exist")

    for t in model.tables.values():
        for mname, expr in t.measures.items():
            check_dax(f"measure [{mname}]", expr)
        for cname, col in t.columns.items():
            if col["expr"]:
                check_dax(f"column {t.name}[{cname}]", col["expr"])
        for kind, src in t.partitions:
            if kind == "calculated":
                check_dax(f"table {t.name}", src, local_cols=t.columns)


# --- PBIR ------------------------------------------------------------------

def _fields(node):
    """Yield (kind, entity, property) for every field reference in a query."""
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            if kind in node and isinstance(node[kind], dict) and "Property" in node[kind]:
                ent = node[kind].get("Expression", {}).get("SourceRef", {}).get("Entity")
                yield kind, ent, node[kind]["Property"]
        for v in node.values():
            yield from _fields(v)
    elif isinstance(node, list):
        for v in node:
            yield from _fields(v)


def check_report(report_dir, model, errors, warnings):
    definition = report_dir / "definition"
    pages_meta = json.loads((definition / "pages" / "pages.json").read_text())
    for pid in pages_meta.get("pageOrder", []):
        if not (definition / "pages" / pid / "page.json").exists():
            errors.append(f"pages.json lists page {pid}, which has no folder")
    if pages_meta.get("activePageName") not in pages_meta.get("pageOrder", []):
        errors.append("pages.json: activePageName is not in pageOrder")

    for page_json in sorted(definition.glob("pages/*/page.json")):
        page = json.loads(page_json.read_text())
        pid = page_json.parent.name
        if page.get("name") != pid:
            errors.append(f"page {pid}: name {page.get('name')} does not match its folder")
        if pid not in pages_meta.get("pageOrder", []):
            warnings.append(f"page {pid} ({page.get('displayName')}) is not in pageOrder")
        pw, ph = page.get("width", 1280), page.get("height", 720)
        boxes = []
        for vjson in sorted(page_json.parent.glob("visuals/*/visual.json")):
            v = json.loads(vjson.read_text())
            vid = vjson.parent.name
            label = f"{page.get('displayName')}/{vid}"
            if v.get("name") != vid:
                errors.append(f"{label}: name does not match its folder")
            pos = v.get("position", {})
            x, y, w, h = (pos.get(k, 0) for k in ("x", "y", "width", "height"))
            if x < 0 or y < 0 or x + w > pw or y + h > ph:
                warnings.append(f"{label}: extends past the {pw}x{ph} page")
            for ox, oy, ow, oh, oid in boxes:
                if x < ox + ow and ox < x + w and y < oy + oh and oy < y + h:
                    warnings.append(f"{label}: overlaps {oid}")
            boxes.append((x, y, w, h, vid))
            natives = {}
            for state in v.get("visual", {}).get("query", {}).get("queryState", {}).values():
                for p in state.get("projections", []):
                    natives.setdefault(p.get("nativeQueryRef"), []).append(p.get("queryRef"))
            for native, refs in natives.items():
                if native is not None and len(set(refs)) > 1:
                    errors.append(f"{label}: {', '.join(refs)} share nativeQueryRef {native!r}; "
                                  "Desktop fails with 'Error fetching data for this visual'")
            if v.get("visual", {}).get("visualType") in ("tableEx", "pivotTable"):
                headers = {}
                for state in v["visual"].get("query", {}).get("queryState", {}).values():
                    for p in state.get("projections", []):
                        field = next(iter(p.get("field", {}).values()), {})
                        header = p.get("displayName") or field.get("Property")
                        headers.setdefault(header, []).append(p.get("queryRef"))
                for header, refs in headers.items():
                    if len(refs) > 1:
                        warnings.append(f"{label}: {len(refs)} columns share the header {header!r} "
                                        f"({', '.join(refs)}); give them labels")
            for kind, ent, prop in _fields(v.get("visual", {}).get("query", {})):
                t = model.tables.get(ent)
                if t is None:
                    errors.append(f"{label}: uses table {ent}, which does not exist")
                elif kind == "Column" and prop not in t.columns:
                    errors.append(f"{label}: uses column {ent}[{prop}], which does not exist")
                elif kind == "Measure" and prop not in t.measures:
                    errors.append(f"{label}: uses measure {ent}[{prop}], which does not exist")
                elif kind == "Column" and t.columns[prop]["props"].get("isHidden") is not None:
                    warnings.append(f"{label}: shows hidden column {ent}[{prop}]")


def check_theme(report_dir, errors):
    """Every registered resource that report.json names must exist."""
    report_json = report_dir / "definition" / "report.json"
    if not report_json.exists():
        return
    report = json.loads(report_json.read_text(encoding="utf-8"))
    for package in report.get("resourcePackages", []):
        for item in package.get("items", []):
            path = report_dir / "StaticResources" / package.get("name", "") / item.get("path", "")
            if not path.is_file():
                errors.append(f"report.json: resource {item.get('name')} has no file at {path.relative_to(report_dir)}")
    custom = report.get("themeCollection", {}).get("customTheme")
    if custom:
        names = {i.get("name") for p in report.get("resourcePackages", []) for i in p.get("items", [])}
        if custom.get("name") not in names:
            errors.append(f"report.json: custom theme {custom.get('name')} is not in resourcePackages")


def check_schemas(root, errors):
    """Validate each JSON file against the published schema its "$schema" names."""
    try:
        import urllib.request
        from jsonschema import Draft7Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7
    except ImportError:
        errors.append("--schemas needs the jsonschema package (pip install jsonschema)")
        return
    cache = {}

    def fetch(uri):
        uri = uri.split("#")[0]
        if uri not in cache:
            with urllib.request.urlopen(uri, timeout=30) as r:
                cache[uri] = json.loads(r.read().decode("utf-8-sig"))
        return cache[uri]

    registry = Registry(retrieve=lambda uri: Resource.from_contents(fetch(uri), default_specification=DRAFT7))
    for f in sorted(root.rglob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        url = doc.get("$schema") if isinstance(doc, dict) else None
        if not url:
            continue
        try:
            validator = Draft7Validator(fetch(url), registry=registry)
        except OSError as e:
            errors.append(f"{f.relative_to(root)}: could not download {url} ({e})")
            continue
        for e in validator.iter_errors(doc):
            where = "/".join(map(str, e.path))
            errors.append(f"{f.relative_to(root)}: schema: /{where}: {e.message[:200]}")


# --- entry -----------------------------------------------------------------

def validate(pbip_path, schemas=False):
    pbip_path = Path(pbip_path)
    errors, warnings = [], []
    root = pbip_path.parent

    for f in list(root.rglob("*.json")) + list(root.rglob("*.pbir")) + list(root.rglob("*.pbism")) + [pbip_path]:
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except ValueError as e:
            errors.append(f"{f.relative_to(root)}: invalid JSON ({e})")
    if errors:
        return errors, warnings

    pbip = json.loads(pbip_path.read_text())
    report_dir = root / pbip["artifacts"][0]["report"]["path"]
    pbir = json.loads((report_dir / "definition.pbir").read_text())
    model_dir = (report_dir / pbir["datasetReference"]["byPath"]["path"]).resolve()
    definition = model_dir / "definition"
    if not definition.is_dir():
        errors.append(f"{model_dir.name}: no TMDL definition folder")
        return errors, warnings

    if schemas:
        check_schemas(root, errors)
    model = parse_tmdl(definition, errors)
    check_model(model, errors, warnings)
    check_theme(report_dir, errors)
    if (report_dir / "definition" / "pages" / "pages.json").exists():
        check_report(report_dir, model, errors, warnings)
    else:
        errors.append(f"{report_dir.name}: no definition/pages/pages.json (not PBIR)")
    return errors, warnings


def main(argv):
    schemas = "--schemas" in argv
    paths = [a for a in argv if a != "--schemas"]
    if not paths:
        print(__doc__)
        return 2
    failed = False
    for path in paths:
        errors, warnings = validate(path, schemas=schemas)
        status = "FAIL" if errors else "ok"
        print(f"{status}  {path}  ({len(errors)} errors, {len(warnings)} warnings)")
        for e in errors:
            print(f"  error: {e}")
        for w in warnings:
            print(f"  warn:  {w}")
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

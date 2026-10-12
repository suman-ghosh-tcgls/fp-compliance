"""Validate a rule set against rule_schema_v0.1.json and the primitive registry.

Usage: python validate_rules.py [rules.json] [schema.json] [primitives.json]
Exit code 0 = valid, 1 = errors found.
"""
import json
import sys

from jsonschema import Draft202012Validator

rules_path = sys.argv[1] if len(sys.argv) > 1 else "udcpr_rules_v1.json"
schema_path = sys.argv[2] if len(sys.argv) > 2 else "rule_schema_v0.1.json"
prims_path = sys.argv[3] if len(sys.argv) > 3 else "primitives.json"

rules = json.load(open(rules_path))
schema = json.load(open(schema_path))
prims = json.load(open(prims_path))["primitives"]

errors = []

# 1. structural validation
v = Draft202012Validator(schema)
for e in sorted(v.iter_errors(rules), key=lambda e: list(e.path)):
    errors.append(f"schema: /{'/'.join(map(str, e.path))}: {e.message}")


# 2. semantic checks the schema cannot express
def exprs(node, path):
    """Yield (path, expr) for every {'primitive': ...} object in the tree."""
    if isinstance(node, dict):
        if "primitive" in node:
            yield path, node
        for k, val in node.items():
            yield from exprs(val, f"{path}/{k}")
    elif isinstance(node, list):
        for i, val in enumerate(node):
            yield from exprs(val, f"{path}/{i}")


ids = set()
for r in rules.get("rules", []):
    rid = r.get("id", "?")
    if rid in ids:
        errors.append(f"{rid}: duplicate rule id")
    ids.add(rid)
    element = r.get("applies_to", {}).get("element")
    check_ids = [c.get("id") for c in r.get("checks", [])]
    if len(check_ids) != len(set(check_ids)):
        errors.append(f"{rid}: duplicate check ids")
    for p, ex in exprs(r, rid):
        name = ex["primitive"]
        if name not in prims:
            errors.append(f"{p}: unknown primitive '{name}'")
            continue
        allowed = prims[name].get("applies_to", [])
        # building-level primitives (height, plot area, count) may be read from any element's building
        building_level = "building" in allowed
        if element and element not in allowed and not building_level:
            errors.append(f"{p}: primitive '{name}' does not apply to element '{element}'")
    for exc in r.get("exceptions", []):
        for cid in exc.get("checks", []):
            if cid not in check_ids:
                errors.append(f"{rid}/exceptions/{exc['id']}: refers to unknown check '{cid}'")

if errors:
    print(f"INVALID: {len(errors)} error(s)")
    for e in errors:
        print("  -", e)
    sys.exit(1)

n_checks = sum(len(r["checks"]) for r in rules["rules"])
used = {ex["primitive"] for r in rules["rules"] for _, ex in exprs(r, "")}
missing = sorted(u for u in used if not prims[u].get("implemented"))
print(f"VALID: {len(rules['rules'])} rules, {n_checks} checks, {len(used)} primitives used")
print(f"primitives not yet implemented ({len(missing)}): {', '.join(missing)}")

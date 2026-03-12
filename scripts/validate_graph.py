import json
import sys
from collections import defaultdict

REQUIRED_BY_TYPE = {
    # Keep this minimal for now; add more as you tighten schema
    "KnownIssue": ["issue_id", "severity", "symptoms", "status"],
    "Service": ["service_id", "status"],
    "Runbook": ["runbook_id", "steps"],
    "SOP": ["sop_id", "steps"],
    "FAQ": ["faq_id", "question", "answer"],
    "FeatureFlag": ["flag_id", "config_area"],
    "Deployment": ["deployment_id", "resource_type"],
    "Release": ["release_id", "version"],
    "Document": ["doc_id", "title"],
}

# Map node "type" -> its primary id field in your JSON
ID_FIELD_BY_TYPE = {
    "KnownIssue": "issue_id",
    "Service": "service_id",
    "Runbook": "runbook_id",
    "SOP": "sop_id",
    "FAQ": "faq_id",
    "FeatureFlag": "flag_id",
    "Deployment": "deployment_id",
    "Release": "release_id",
    "Document": "doc_id",
}

def load(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(path: str):
    data = load(path)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    errors = []
    warnings = []

    # 1) Build index of all nodes by (type, id) and also global id collision check
    by_type_id = {}
    global_ids = defaultdict(list)

    for i, n in enumerate(nodes):
        ntype = n.get("type")
        if not ntype:
            errors.append(f"Node[{i}] missing 'type'")
            continue

        id_field = ID_FIELD_BY_TYPE.get(ntype)
        if not id_field:
            warnings.append(f"Node[{i}] unknown type '{ntype}' (no id-field mapping); skipping strict checks")
            continue

        nid = n.get(id_field)
        if not nid:
            errors.append(f"Node[{i}] type={ntype} missing '{id_field}'")
            continue

        key = (ntype, nid)
        if key in by_type_id:
            errors.append(f"Duplicate node id: type={ntype} {id_field}={nid}")
        by_type_id[key] = n

        global_ids[nid].append(ntype)

    # Duplicate IDs across different types (not always fatal, but dangerous)
    for nid, types in global_ids.items():
        if len(set(types)) > 1:
            warnings.append(f"ID '{nid}' appears across multiple types: {sorted(set(types))}")

    # 2) Missing required fields
    for (ntype, nid), n in by_type_id.items():
        req = REQUIRED_BY_TYPE.get(ntype, [])
        missing = [k for k in req if n.get(k) in (None, "", [], {})]
        if missing:
            errors.append(f"{ntype}({nid}) missing/empty required fields: {missing}")

    # 3) Broken edges + collect used node IDs
    used = set()
    for j, e in enumerate(edges):
        src = e.get("source")
        tgt = e.get("target")
        etype = e.get("type")
        if not src or not tgt or not etype:
            errors.append(f"Edge[{j}] missing source/target/type: {e}")
            continue

        used.add(src)
        used.add(tgt)

        # We can only validate existence if we can find src/tgt in ANY node id field
        # So build a helper set of all ids present
    all_node_ids = set(global_ids.keys())

    for j, e in enumerate(edges):
        src = e.get("source")
        tgt = e.get("target")
        if src and src not in all_node_ids:
            errors.append(f"Edge[{j}] broken source '{src}' not found in nodes")
        if tgt and tgt not in all_node_ids:
            errors.append(f"Edge[{j}] broken target '{tgt}' not found in nodes")

    # 4) Orphan nodes (never referenced by any edge)
    orphans = []
    for nid in all_node_ids:
        if nid not in used:
            orphans.append(nid)
    if orphans:
        warnings.append(f"Orphan node IDs (not referenced in any edge): {orphans[:50]}{'...' if len(orphans)>50 else ''}")

    # Output
    ok = len(errors) == 0
    print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings}, indent=2))

    # Exit code: fail CI/seed if errors
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    graph_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/knowledge_graph.json"
    main(graph_path)

#run it - python scripts/validate_graph.py scripts/knowledge_graph.json
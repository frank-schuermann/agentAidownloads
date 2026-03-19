import json

with open("knowledge_graph_generated.json", "r", encoding="utf-8") as f:
    g = json.load(f)

print("=== KnownIssue Nodes ===")
for n in g["nodes"]:
    if n["type"] == "KnownIssue":
        print(f"  {n['id']:40s}  {n['label'][:70]}")

print("\n=== Runbook Nodes ===")
for n in g["nodes"]:
    if n["type"] == "Runbook":
        print(f"  {n['id']:40s}  {n['label'][:70]}")

print("\n=== SOP Nodes ===")
for n in g["nodes"]:
    if n["type"] == "SOP":
        print(f"  {n['id']:40s}  {n['label'][:70]}")

print("\n=== Service Nodes ===")
for n in g["nodes"]:
    if n["type"] == "Service":
        print(f"  {n['id']:40s}  {n['label'][:70]}")

print(f"\n=== Existing Edges with HAS_KNOWN_ISSUE ===")
for e in g["edges"]:
    if e["type"] == "HAS_KNOWN_ISSUE":
        print(f"  {e['source']} --> {e['target']}")

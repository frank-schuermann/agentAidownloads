import json
from pathlib import Path
import sys

# Ensure project root (kg/) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.issue_router import resolve_known_issue_from_text


TEST_QUERIES = [
    "Known Issue: QM scorecards show inconsistent results across runs",
]


def main():
    tenant_id = "tenant_demo"
    kg = KnowledgeGraphService(tenant_id)

    for query in TEST_QUERIES:
        print("\n" + "=" * 120)
        print(f"QUERY: {query}")
        print("=" * 120)

        result = resolve_known_issue_from_text(kg, query, limit=3)

        print("\nFULL RESULT:\n")
        print(json.dumps(result, indent=2, default=str))

        print("\nSUMMARY:")
        print(f"selected_issue_id: {result.get('selected_issue_id')}")
        candidate_list = result.get("candidates", [])
        if candidate_list:
            print(f"top_candidate: {candidate_list[0]}")
        else:
            print("top_candidate: None")

        selected_context = result.get("selected_context")
        if selected_context:
            affected = selected_context.get("affected", {})
            services = affected.get("services", [])
            print(f"affected_services_count: {len(services)}")
        else:
            print("selected_context: None")

    debug_file = PROJECT_ROOT / "rag_debug" / "last_rag_result.json"
    print("\n" + "-" * 120)
    print(f"RAG debug file expected at: {debug_file}")
    print(f"Exists: {debug_file.exists()}")


if __name__ == "__main__":
    main()
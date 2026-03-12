import json

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.issue_router import resolve_known_issue_from_text


TEST_QUERIES = [
    " SSO login failures (SAML session invalid / login loop)",
]


def main():
    tenant_id = "tenant_demo"
    kg = KnowledgeGraphService(tenant_id)

    for query in TEST_QUERIES:
        print("\n" + "=" * 120)
        print(f"QUERY: {query}")
        print("=" * 120)

        result = resolve_known_issue_from_text(kg, query, limit=3)

        print("\nSELECTED ISSUE ID:")
        print(result.get("selected_issue_id"))

        print("\nCANDIDATES:")
        print(json.dumps(result.get("candidates", []), indent=2, default=str))

        print("\nLLM ANSWER:")
        print(result.get("llm_answer"))

        llm_context = result.get("llm_context") or {}
        required_docs = llm_context.get("required_docs", {})
        optional_docs = llm_context.get("optional_docs", {})

        print("\nREQUIRED DOCS FOUND:")
        print(json.dumps(
            {
                "known_issue_doc": required_docs.get("known_issue_doc", {}).get("file_name") if required_docs.get("known_issue_doc") else None,
                "runbook_doc": required_docs.get("runbook_doc", {}).get("file_name") if required_docs.get("runbook_doc") else None,
                "sop_doc": required_docs.get("sop_doc", {}).get("file_name") if required_docs.get("sop_doc") else None,
            },
            indent=2
        ))

        print("\nOPTIONAL DOCS FOUND:")
        print(json.dumps(
            {
                "faq_doc": optional_docs.get("faq_doc", {}).get("file_name") if optional_docs.get("faq_doc") else None,
                "guide_doc": optional_docs.get("guide_doc", {}).get("file_name") if optional_docs.get("guide_doc") else None,
                "release_doc": optional_docs.get("release_doc", {}).get("file_name") if optional_docs.get("release_doc") else None,
            },
            indent=2
        ))

        print("\nRAW RESULT KEYS:")
        print(list(result.keys()))

        issue_id = result.get("selected_issue_id") or "unknown_issue"
        output_file = f"issue_router_result_{issue_id}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str, ensure_ascii=False)



    print("\nDone.")


if __name__ == "__main__":
    main()
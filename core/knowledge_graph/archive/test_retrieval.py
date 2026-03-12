from pathlib import Path
from retriever import HybridRetriever


BASE_DIR = Path(__file__).resolve().parents[3]
CHROMA_DIR = BASE_DIR / "chroma_store"


TEST_QUERIES = [
    "Known Issue: QM scorecards show inconsistent results across runs",
]


def print_results(title: str, results: list[dict], limit: int = 3):
    print(f"\n--- {title} ---")
    for i, r in enumerate(results[:limit], start=1):
        metadata = r.get("metadata", {})
        print(f"\nRank {i}")
        print(f"ID: {r.get('id')}")
        print(f"Doc Type: {metadata.get('doc_type')}")
        print(f"Entity ID: {metadata.get('entity_id')}")
        print(f"File Name: {metadata.get('file_name')}")
        print(f"Primary Category: {metadata.get('primary_category')}")
        print(f"Sources: {r.get('sources', r.get('retrieval_type'))}")
        print(f"Score: {r.get('rrf_score', r.get('score'))}")
        print(f"Text Preview: {r.get('text', '')[:250]}...")

def print_grouped_results(title: str, results: list[dict], limit: int = 3):
    print(f"\n--- {title} ---")
    for i, r in enumerate(results[:limit], start=1):
        print(f"\nRank {i}")
        print(f"Entity ID: {r.get('entity_id')}")
        print(f"Doc Type: {r.get('doc_type')}")
        print(f"File Name: {r.get('file_name')}")
        print(f"Primary Category: {r.get('primary_category')}")
        print(f"Best Chunk ID: {r.get('best_chunk_id')}")
        print(f"Sources: {r.get('sources')}")
        print(f"Best Score: {r.get('best_score')}")
        print(f"Supporting Chunks: {r.get('supporting_chunks')}")
        print(f"Text Preview: {r.get('best_text', '')[:250]}...")


def main():
    retriever = HybridRetriever(
        persist_directory=str(CHROMA_DIR),
        collection_name="kg_rag_collection",
        top_k=5,
    )

    for query in TEST_QUERIES:
        print("\n" + "=" * 100)
        print(f"QUERY: {query}")
        print("=" * 100)

        results = retriever.hybrid_search(query, top_k=5)

        print_results("Semantic Results", results["semantic_results"])
        print_results("Keyword Results", results["keyword_results"])
        print_results("Fused Results (RRF)", results["fused_results"])
        print_results("Boosted Results", results["boosted_results"])
        print_grouped_results("Grouped Entity Results", results["grouped_results"])


if __name__ == "__main__":
    main()
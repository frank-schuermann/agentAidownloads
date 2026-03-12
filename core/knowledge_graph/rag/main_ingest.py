from pathlib import Path

from document_loader import DocumentLoader, DocumentChunker
from local_embedder import LocalEmbedder
from chroma_indexer import ChromaIndexer


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data" / "kg_docs"
CHROMA_DIR = BASE_DIR / "chroma_store"


def main():
    loader = DocumentLoader()
    chunker = DocumentChunker()

    print("Loading documents...")
    docs = loader.load_directory(str(DATA_DIR))
    print(f"Loaded {len(docs)} documents")

    if docs:
        print("\nSample loaded document metadata:")
        print(docs[0].metadata)

    print("\nChunking documents...")
    chunks = chunker.chunk_documents(docs)
    print(f"Created {len(chunks)} chunks")

    if not chunks:
        raise ValueError(f"No chunks created. Check {DATA_DIR}")

    print("\nGenerating local embeddings...")
    embedder = LocalEmbedder()
    embedded_chunks = embedder.embed_chunks(chunks)
    print(f"Generated embeddings for {len(embedded_chunks)} chunks")

    print("\nSaving to ChromaDB...")
    indexer = ChromaIndexer(
        persist_directory=str(CHROMA_DIR),
        collection_name="kg_rag_collection"
    )

    indexer.reset_collection()
    indexer.add_documents(embedded_chunks)

    print(f"Chroma collection count: {indexer.count()}")

    sample = indexer.peek(limit=2)
    print("\nSample Chroma peek:")
    print(sample)


if __name__ == "__main__":
    main()
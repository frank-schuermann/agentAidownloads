from document_loader import DocumentLoader, DocumentChunker
from azure_embedder import AzureEmbedder
from azure_search_indexer import AzureSearchIndexer


def main():
    loader = DocumentLoader()
    chunker = DocumentChunker()

    docs = loader.load_directory("./data/kg_docs")
    chunks = chunker.chunk_documents(docs)

    embedder = AzureEmbedder.from_env()
    embedded_chunks = embedder.embed_chunks(chunks)

    if not embedded_chunks:
        raise ValueError("No embedded chunks generated.")

    vector_dimensions = len(embedded_chunks[0]["content_vector"])

    indexer = AzureSearchIndexer.from_env(vector_dimensions=vector_dimensions)
    indexer.create_or_update_index()

    results = indexer.upload_documents(embedded_chunks)

    print(f"Uploaded {len(results)} documents")
    print(results[:5])


if __name__ == "__main__":
    main()
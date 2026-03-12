from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer


@dataclass
class LocalEmbeddingConfig:
    model_name: str = "BAAI/bge-small-en-v1.5"
    normalize_embeddings: bool = True


class LocalEmbedder:
    """
    Generates embeddings locally using Sentence Transformers.
    """

    def __init__(self, config: Optional[LocalEmbeddingConfig] = None):
        self.config = config or LocalEmbeddingConfig()
        self.model = SentenceTransformer(self.config.model_name)

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")

        embedding = self.model.encode(
            text,
            normalize_embeddings=self.config.normalize_embeddings,
        )
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        cleaned = [t.strip() for t in texts if t and t.strip()]
        if not cleaned:
            return []

        embeddings = self.model.encode(
            cleaned,
            normalize_embeddings=self.config.normalize_embeddings,
        )
        return embeddings.tolist()

    def embed_chunks(self, chunks: List[Any]) -> List[Dict[str, Any]]:
        if not chunks:
            return []

        texts = [chunk.text for chunk in chunks]
        vectors = self.embed_texts(texts)

        embedded_chunks: List[Dict[str, Any]] = []

        for chunk, vector in zip(chunks, vectors):
            embedded_chunks.append({
                "id": chunk.chunk_id,
                "chunk_id": chunk.chunk_id,
                "entity_id": chunk.entity_id,
                "doc_type": chunk.doc_type,
                "file_name": chunk.file_name,
                "text": chunk.text,
                "content_vector": vector,
                **chunk.metadata,
            })

        return embedded_chunks
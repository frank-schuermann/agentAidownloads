from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


@dataclass
class EmbeddingConfig:
    azure_endpoint: str
    api_key: str
    api_version: str
    embedding_model: str


class AzureEmbedder:
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client = AzureOpenAI(
            azure_endpoint=config.azure_endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
        )

    @classmethod
    def from_env(cls) -> "AzureEmbedder":
        config = EmbeddingConfig(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            embedding_model=os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
        )

        if not config.azure_endpoint:
            raise ValueError("Missing AZURE_OPENAI_ENDPOINT in .env")
        if not config.api_key:
            raise ValueError("Missing AZURE_OPENAI_API_KEY in .env")

        return cls(config)

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")

        response = self.client.embeddings.create(
            model=self.config.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        cleaned = [t.strip() for t in texts if t and t.strip()]
        if not cleaned:
            return []

        response = self.client.embeddings.create(
            model=self.config.embedding_model,
            input=cleaned
        )
        return [item.embedding for item in response.data]

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
                **chunk.metadata
            })

        return embedded_chunks
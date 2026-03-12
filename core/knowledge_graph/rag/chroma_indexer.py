from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings


class ChromaIndexer:
    def __init__(
        self,
        persist_directory: str = "./chroma_store",
        collection_name: str = "kg_rag_collection",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "KG + RAG document collection"}
        )

    def reset_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "KG + RAG document collection"}
        )

    def add_documents(self, embedded_chunks: List[Dict[str, Any]]) -> None:
        if not embedded_chunks:
            return

        ids: List[str] = []
        documents: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict[str, Any]] = []

        for chunk in embedded_chunks:
            metadata = dict(chunk)
            metadata.pop("text", None)
            metadata.pop("content_vector", None)

            clean_metadata: Dict[str, Any] = {}

            for k, v in metadata.items():
                if v is None:
                    continue
                elif isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                elif isinstance(v, list):
                    clean_metadata[k] = json.dumps(v)
                elif isinstance(v, dict):
                    clean_metadata[k] = json.dumps(v)
                else:
                    clean_metadata[k] = str(v)

            ids.append(chunk["id"])
            documents.append(chunk["text"])
            embeddings.append(chunk["content_vector"])
            metadatas.append(clean_metadata)

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def count(self) -> int:
        return self.collection.count()

    def peek(self, limit: int = 5) -> Dict[str, Any]:
        return self.collection.peek(limit=limit)
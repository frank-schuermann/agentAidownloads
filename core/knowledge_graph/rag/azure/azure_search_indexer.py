from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

load_dotenv()


@dataclass
class AzureSearchConfig:
    endpoint: str
    api_key: str
    index_name: str
    vector_dimensions: int


class AzureSearchIndexer:
    """
    Creates Azure AI Search index and uploads embedded chunks.
    """

    def __init__(self, config: AzureSearchConfig):
        self.config = config
        credential = AzureKeyCredential(config.api_key)

        self.index_client = SearchIndexClient(
            endpoint=config.endpoint,
            credential=credential,
        )

        self.search_client = SearchClient(
            endpoint=config.endpoint,
            index_name=config.index_name,
            credential=credential,
        )

    @classmethod
    def from_env(cls, vector_dimensions: int) -> "AzureSearchIndexer":
        endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "").strip()
        api_key = os.getenv("AZURE_AI_SEARCH_API_KEY", "").strip()
        index_name = os.getenv("AZURE_AI_SEARCH_INDEX_NAME", "").strip()

        if not endpoint:
            raise ValueError("Missing AZURE_AI_SEARCH_ENDPOINT in .env")
        if not api_key:
            raise ValueError("Missing AZURE_AI_SEARCH_API_KEY in .env")
        if not index_name:
            raise ValueError("Missing AZURE_AI_SEARCH_INDEX_NAME in .env")

        return cls(
            AzureSearchConfig(
                endpoint=endpoint,
                api_key=api_key,
                index_name=index_name,
                vector_dimensions=vector_dimensions,
            )
        )

    def build_index_schema(self) -> SearchIndex:
        """
        Build Azure AI Search index schema for KG/RAG chunks.
        """

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),

            SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="entity_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="doc_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="file_name", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),

            SearchField(
                name="text",
                type=SearchFieldDataType.String,
                searchable=True,
            ),

            SimpleField(name="format", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="primary_category", type=SearchFieldDataType.String, filterable=True, facetable=True),

            SearchField(
                name="category_tags",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                searchable=True,
                filterable=True,
                facetable=True,
            ),

            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.config.vector_dimensions,
                vector_search_profile_name="default-vector-profile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="default-hnsw"
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="default-hnsw",
                )
            ],
        )

        return SearchIndex(
            name=self.config.index_name,
            fields=fields,
            vector_search=vector_search,
        )

    def create_or_update_index(self) -> None:
        """
        Create index if missing, otherwise update it.
        """
        index = self.build_index_schema()
        self.index_client.create_or_update_index(index)

    def upload_documents(self, embedded_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Upload embedded chunk documents into Azure AI Search.
        """
        if not embedded_chunks:
            return []

        results = self.search_client.upload_documents(documents=embedded_chunks)
        return [
            {
                "key": r.key,
                "succeeded": r.succeeded,
                "error_message": getattr(r, "error_message", None),
            }
            for r in results
        ]
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi

from core.knowledge_graph.rag.local_embedder import LocalEmbedder


class HybridRetriever:
    DOC_TYPE_KEYWORDS = {
        "KnownIssue": ["known issue", "issue", "problem", "bug"],
        "Runbook": ["runbook", "recovery", "steps", "fix steps"],
        "SOP": ["sop", "procedure", "communications", "playbook"],
        "FAQ": ["faq", "why", "how do i", "common question"],
        "UserGuide": ["guide", "user guide", "admin guide", "documentation"],
        "ReleaseNote": ["release note", "release", "what changed", "version"],
    }

    CATEGORY_KEYWORDS = {
        "voice": ["voice", "call", "transfer", "warm transfer", "cold transfer", "acs"],
        "chat": ["chat", "widget", "messaging", "web chat"],
        "copilot": ["copilot", "summary", "summarization", "hallucination", "draft"],
        "qm": ["quality", "qm", "scorecard", "rubric", "evaluation", "calibration"],
        "wfm": ["wfm", "forecast", "schedule", "staffing", "intraday"],
        "routing": ["routing", "queue", "workstream", "assignment", "overflow"],
        "latency": ["slow", "latency", "delay", "timeout"],
        "outage": ["outage", "down", "failure", "unavailable", "drop"],
        "sso": ["sso", "login", "saml", "oauth", "authentication", "identity"],
    }

    def __init__(
        self,
        persist_directory: str = "./chroma_store",
        collection_name: str = "kg_rag_collection",
        top_k: int = 5,
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.top_k = top_k

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_collection(self.collection_name)
        self.embedder = LocalEmbedder()

        self.all_docs = self._load_all_documents()
        self.bm25 = self._build_bm25_index(self.all_docs)

    def _load_all_documents(self) -> List[Dict[str, Any]]:
        data = self.collection.get(include=["documents", "metadatas"])

        docs: List[Dict[str, Any]] = []
        ids = data.get("ids", [])
        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])

        for doc_id, text, metadata in zip(ids, documents, metadatas):
            docs.append({
                "id": doc_id,
                "text": text,
                "metadata": metadata or {}
            })

        return docs

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _build_bm25_index(self, docs: List[Dict[str, Any]]) -> BM25Okapi:
        tokenized_corpus = [self._tokenize(doc["text"]) for doc in docs]
        return BM25Okapi(tokenized_corpus)

    def semantic_search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        top_k = top_k or self.top_k
        query_vector = self.embedder.embed_text(query)

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        output: List[Dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for rank, (doc_id, text, meta, distance) in enumerate(zip(ids, documents, metadatas, distances), start=1):
            output.append({
                "id": doc_id,
                "text": text,
                "metadata": meta or {},
                "score": float(distance),
                "rank": rank,
                "retrieval_type": "semantic"
            })

        return output

    def keyword_search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        top_k = top_k or self.top_k
        query_tokens = self._tokenize(query)

        scores = self.bm25.get_scores(query_tokens)
        ranked = sorted(zip(self.all_docs, scores), key=lambda x: x[1], reverse=True)[:top_k]

        output: List[Dict[str, Any]] = []
        for rank, (doc, score) in enumerate(ranked, start=1):
            output.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": float(score),
                "rank": rank,
                "retrieval_type": "keyword"
            })

        return output

    def reciprocal_rank_fusion(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        fused: Dict[str, Dict[str, Any]] = {}

        for results in [semantic_results, keyword_results]:
            for result in results:
                doc_id = result["id"]
                rank = result["rank"]
                rrf_score = 1.0 / (k + rank)

                if doc_id not in fused:
                    fused[doc_id] = {
                        "id": doc_id,
                        "text": result["text"],
                        "metadata": result["metadata"],
                        "rrf_score": 0.0,
                        "sources": [],
                    }

                fused[doc_id]["rrf_score"] += rrf_score
                fused[doc_id]["sources"].append(result["retrieval_type"])

        fused_results = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)

        for idx, item in enumerate(fused_results, start=1):
            item["rank"] = idx

        return fused_results

    def _doc_type_boost(self, query: str, doc_type: str) -> float:
        query_lower = query.lower()
        boost = 0.0

        for dtype, keywords in self.DOC_TYPE_KEYWORDS.items():
            if dtype != doc_type:
                continue
            for kw in keywords:
                if kw in query_lower:
                    boost += 0.05

        return boost

    def _category_boost(self, query: str, primary_category: Optional[str]) -> float:
        if not primary_category:
            return 0.0

        query_lower = query.lower()
        keywords = self.CATEGORY_KEYWORDS.get(primary_category, [])
        score = 0.0

        for kw in keywords:
            if kw in query_lower:
                score += 0.03

        return score

    def apply_boosts(self, query: str, fused_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        boosted = []

        for result in fused_results:
            metadata = result.get("metadata", {})
            doc_type = metadata.get("doc_type")
            primary_category = metadata.get("primary_category")

            final_score = result["rrf_score"]
            final_score += self._doc_type_boost(query, doc_type)
            final_score += self._category_boost(query, primary_category)

            item = dict(result)
            item["final_score"] = final_score
            boosted.append(item)

        boosted.sort(key=lambda x: x["final_score"], reverse=True)

        for idx, item in enumerate(boosted, start=1):
            item["rank"] = idx

        return boosted

    def group_by_entity(self, boosted_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for result in boosted_results:
            metadata = result.get("metadata", {})
            entity_id = metadata.get("entity_id") or result["id"]

            if entity_id not in grouped:
                grouped[entity_id] = {
                    "entity_id": entity_id,
                    "doc_type": metadata.get("doc_type"),
                    "file_name": metadata.get("file_name"),
                    "primary_category": metadata.get("primary_category"),
                    "best_chunk_id": result["id"],
                    "best_text": result["text"],
                    "best_score": result["final_score"],
                    "sources": set(result.get("sources", [])),
                    "supporting_chunks": [result["id"]],
                    "supporting_results": [result],
                }
            else:
                grouped[entity_id]["supporting_chunks"].append(result["id"])
                grouped[entity_id]["supporting_results"].append(result)
                grouped[entity_id]["sources"].update(result.get("sources", []))
                if result["final_score"] > grouped[entity_id]["best_score"]:
                    grouped[entity_id]["best_score"] = result["final_score"]
                    grouped[entity_id]["best_chunk_id"] = result["id"]
                    grouped[entity_id]["best_text"] = result["text"]

        grouped_results = list(grouped.values())
        grouped_results.sort(key=lambda x: x["best_score"], reverse=True)

        for idx, item in enumerate(grouped_results, start=1):
            item["rank"] = idx
            item["sources"] = list(item["sources"])

        return grouped_results

    def hybrid_search(self, query: str, top_k: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        top_k = top_k or self.top_k

        semantic_results = self.semantic_search(query, top_k=top_k)
        keyword_results = self.keyword_search(query, top_k=top_k)
        fused_results = self.reciprocal_rank_fusion(semantic_results, keyword_results)
        boosted_results = self.apply_boosts(query, fused_results)
        grouped_results = self.group_by_entity(boosted_results)

        return {
            "semantic_results": semantic_results,
            "keyword_results": keyword_results,
            "fused_results": fused_results[:top_k],
            "boosted_results": boosted_results[:top_k],
            "grouped_results": grouped_results[:top_k],
        }
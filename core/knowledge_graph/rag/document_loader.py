from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class KGDocType(str, Enum):
    KNOWN_ISSUE = "KnownIssue"
    SERVICE = "Service"
    RUNBOOK = "Runbook"
    SOP = "SOP"
    CUSTOMER = "Customer"
    FAQ = "FAQ"
    ENGINEER = "Engineer"
    INCIDENT = "Incident"
    DEPLOYMENT = "Deployment"
    FEATURE_FLAG = "FeatureFlag"
    USER_GUIDE = "UserGuide"
    RELEASE_NOTE = "ReleaseNote"
    UNKNOWN = "Unknown"


@dataclass
class ChunkConfig:
    chunk_size: int = 1000
    chunk_overlap: int = 150
    min_chunk_size: int = 100


@dataclass
class LoadedDocument:
    file_name: str
    file_path: str
    doc_type: KGDocType
    entity_id: Optional[str]
    content: str
    metadata: Dict[str, Any]


@dataclass
class DocumentChunk:
    chunk_id: str
    entity_id: Optional[str]
    doc_type: str
    file_name: str
    text: str
    metadata: Dict[str, Any]


class DocumentTypeMapper:
    PREFIX_MAP = {
        "knownissue": KGDocType.KNOWN_ISSUE,
        "service": KGDocType.SERVICE,
        "runbook": KGDocType.RUNBOOK,
        "sop": KGDocType.SOP,
        "customer": KGDocType.CUSTOMER,
        "faq": KGDocType.FAQ,
        "engineer": KGDocType.ENGINEER,
        "expert": KGDocType.ENGINEER,
        "incident": KGDocType.INCIDENT,
        "infra": KGDocType.DEPLOYMENT,
        "deployment": KGDocType.DEPLOYMENT,
        "config": KGDocType.FEATURE_FLAG,
        "configuration": KGDocType.FEATURE_FLAG,
        "userguide": KGDocType.USER_GUIDE,
        "releasenotes": KGDocType.RELEASE_NOTE,
        "release": KGDocType.RELEASE_NOTE,
    }

    @classmethod
    def infer_doc_type(cls, file_name: str) -> KGDocType:
        stem = Path(file_name).stem.lower()
        normalized = re.sub(r"[^a-z]", "", stem)

        for prefix, doc_type in cls.PREFIX_MAP.items():
            if normalized.startswith(prefix):
                return doc_type

        first_token = re.split(r"[_\-\s]", Path(file_name).stem.lower())[0]
        return cls.PREFIX_MAP.get(first_token, KGDocType.UNKNOWN)


class EntityIdExtractor:
    ID_PATTERNS = [
        r"\bKI-\d+(?:-\d+)*\b",
        r"\bSVC-\d+(?:-\d+)*\b",
        r"\bRB-\d+(?:-\d+)*\b",
        r"\bSOP-\d+(?:-\d+)*\b",
        r"\bCUST-\d+(?:-\d+)*\b",
        r"\bFAQ-\d+(?:-\d+)*\b",
        r"\bENG-\d+(?:-\d+)*\b",
        r"\bEXP-\d+(?:-\d+)*\b",
        r"\bINC-\d+(?:-\d+)*\b",
        r"\bINFRA-\d+(?:-\d+)*\b",
        r"\bCFG-\d+(?:-\d+)*\b",
        r"\bUG-\d+(?:-\d+)*\b",
        r"\bRN-\d+(?:-\d+)*\b",
    ]

    @classmethod
    def extract_entity_id(cls, text: str, file_name: str) -> Optional[str]:
        combined = f"{file_name}\n{text}"

        for pattern in cls.ID_PATTERNS:
            match = re.search(pattern, combined, re.IGNORECASE)
            if match:
                entity_id = match.group(0).upper()
                if entity_id.startswith("EXP-"):
                    return entity_id.replace("EXP-", "ENG-")
                return entity_id

        return None


class CategoryTagger:
    """
    Assigns searchable category tags based on technical keywords.
    """

    KEYWORD_MAP = {
        "outage": ["outage", "down", "unavailable", "error", "failure", "drop"],
        "latency": ["slow", "delay", "latency", "timeout", "spinning"],
        "routing": ["routing", "queue", "workstream", "assignment", "overflow"],
        "voice": ["voice", "call", "transfer", "warm transfer", "cold transfer", "acs"],
        "chat": ["chat", "widget", "live chat", "web chat", "messaging"],
        "copilot": ["copilot", "suggestion", "draft", "summarization", "summary", "hallucination"],
        "knowledge": ["knowledge", "kb", "article", "documentation"],
        "wfm": ["wfm", "workforce", "forecast", "schedule", "intraday", "staffing", "regenerate", "regen", "jobs"],
        "qm": ["quality", "qm", "scorecard", "evaluation", "rubric", "calibration", "review"],
        "sso": ["sso", "saml", "oauth", "oidc", "login", "authentication", "identity", "assertion"],
    }

    @classmethod
    def extract_category_info(cls, text: str, file_name: str = "") -> Dict[str, Any]:
        haystack = f"{file_name}\n{text}".lower()
        scores: Dict[str, int] = {}

        for category, keywords in cls.KEYWORD_MAP.items():
            score = 0
            for kw in keywords:
                if kw.lower() in haystack:
                    score += 1
            if score > 0:
                scores[category] = score

        tags = sorted(scores.keys())
        primary = max(scores, key=scores.get) if scores else None

        return {
            "category_tags": tags,
            "primary_category": primary,
            "category_scores": scores
        }


class DocumentLoader:
    SUPPORTED_EXTENSIONS = {".txt"}

    def load_file(self, file_path: str) -> LoadedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        content = path.read_text(encoding="utf-8").strip()
        doc_type = DocumentTypeMapper.infer_doc_type(path.name)
        entity_id = EntityIdExtractor.extract_entity_id(content, path.name)

        category_info = CategoryTagger.extract_category_info(content, path.name)

        metadata = {
            "source": str(path),
            "file_name": path.name,
            "doc_type": doc_type.value,
            "entity_id": entity_id,
            "format": "text",
            **category_info,
        }

        return LoadedDocument(
            file_name=path.name,
            file_path=str(path),
            doc_type=doc_type,
            entity_id=entity_id,
            content=content,
            metadata=metadata,
        )

    def load_directory(self, directory_path: str, recursive: bool = True) -> List[LoadedDocument]:
        base = Path(directory_path)
        if not base.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        pattern = "**/*" if recursive else "*"
        files = [
            p for p in base.glob(pattern)
            if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ]

        documents: List[LoadedDocument] = []
        for file_path in sorted(files):
            documents.append(self.load_file(str(file_path)))

        return documents


class DocumentChunker:
    def __init__(self, config: Optional[ChunkConfig] = None):
        self.config = config or ChunkConfig()

    def chunk_document(self, doc: LoadedDocument) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        text = doc.content

        start = 0
        chunk_index = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.config.chunk_size, text_len)
            chunk_text = text[start:end].strip()

            if len(chunk_text) >= self.config.min_chunk_size:
                safe_file_stem = Path(doc.file_name).stem.replace(" ", "_")
                base_id = doc.entity_id or safe_file_stem
                chunk_id = f"{base_id}__{safe_file_stem}__chunk_{chunk_index}"

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        entity_id=doc.entity_id,
                        doc_type=doc.doc_type.value,
                        file_name=doc.file_name,
                        text=chunk_text,
                        metadata={
                            **doc.metadata,
                            "chunk_index": chunk_index,
                            "chunk_start": start,
                            "chunk_end": end,
                        },
                    )
                )
                chunk_index += 1

            if end == text_len:
                break

            start = max(0, end - self.config.chunk_overlap)

        return chunks

    def chunk_documents(self, docs: List[LoadedDocument]) -> List[DocumentChunk]:
        all_chunks: List[DocumentChunk] = []
        for doc in docs:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks


if __name__ == "__main__":
    loader = DocumentLoader()
    chunker = DocumentChunker()

    docs = loader.load_directory("./data", recursive=True)
    chunks = chunker.chunk_documents(docs)

    print(f"Loaded documents: {len(docs)}")
    print(f"Created chunks: {len(chunks)}")

    if docs:
        print("\nSample loaded document:")
        print(docs[0])

    if chunks:
        print("\nSample chunk:")
        print(chunks[0])
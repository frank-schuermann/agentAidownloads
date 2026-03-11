"""
Bulk Document Import Service

Imports multiple documents from ZIP archives into the Knowledge Graph
with intelligent edge inference.

Use Case: Upload a ZIP file with Runbooks, FAQs, User Guides, SOPs, SPOs
and automatically create nodes + infer relationships.
"""

import json
import logging
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from io import BytesIO

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.models.nodes import (
    DocumentNode, FAQNode, RunbookNode, SOPNode, KnownIssueNode
)
from core.knowledge_graph.models.enums import (
    DocumentType, DocumentSource, SOPCategory, RunbookType,
    KnownIssueSeverity, KnownIssueStatus
)

logger = logging.getLogger(__name__)


# =============================================================================
# Document Type Detection
# =============================================================================
@dataclass
class DocumentMetadata:
    """Metadata extracted from document filename and content."""
    doc_id: str
    filename: str
    title: str
    doc_type: str  # Runbook, FAQ, SOP, UserGuide, KnownIssue, SPO, Document
    node_label: str  # Neo4j node label
    content: str
    extracted_refs: Set[str] = field(default_factory=set)
    keywords: Set[str] = field(default_factory=set)
    category: Optional[str] = None
    priority: Optional[str] = None


class DocumentTypeDetector:
    """Detects document type from filename and content."""
    
    # Filename patterns
    PATTERNS = {
        "Runbook": r"^(Runbook|RB|RUNBOOK)[-_]",
        "KnownIssue": r"^(KnownIssue|KI|KNOWN[-_]ISSUE)[-_]",
        "FAQ": r"^(FAQ|Faq)[-_]",
        "SOP": r"^(SOP|Sop)[-_]",
        "SPO": r"^(SPO|Spo)[-_]",
        "UserGuide": r"^(UserGuide|UG|USER[-_]GUIDE|Guide)[-_]",
        "Configuration": r"^(Configuration|Config|CFG)[-_]",
        "Infrastructure": r"^(Infrastructure|Infra|INFRA)[-_]",
        "ReleaseNote": r"^(ReleaseNote|Release|REL)[-_]",
    }
    
    # Content indicators
    CONTENT_KEYWORDS = {
        "Runbook": ["diagnostic", "remediation", "troubleshoot", "steps to resolve"],
        "SOP": ["standard operating procedure", "approval required", "escalation"],
        "FAQ": ["question:", "answer:", "frequently asked"],
        "KnownIssue": ["known issue", "symptom", "workaround", "root cause"],
        "UserGuide": ["how to", "user guide", "setup instructions"],
    }
    
    # Node label mapping
    NODE_LABELS = {
        "Runbook": "Runbook",
        "KnownIssue": "KnownIssue",
        "FAQ": "FAQ",
        "SOP": "SOP",
        "SPO": "Document",  # SPOs are special documents
        "UserGuide": "Document",
        "Configuration": "Document",
        "Infrastructure": "Document",
        "ReleaseNote": "Document",
        "Document": "Document",
    }
    
    @classmethod
    def detect(cls, filename: str, content: str) -> Tuple[str, str]:
        """
        Detect document type and node label.
        
        Returns:
            (doc_type, node_label)
        """
        # Check filename patterns first
        for doc_type, pattern in cls.PATTERNS.items():
            if re.search(pattern, filename, re.IGNORECASE):
                return doc_type, cls.NODE_LABELS.get(doc_type, "Document")
        
        # Check content keywords
        content_lower = content.lower()
        best_match = None
        best_score = 0
        
        for doc_type, keywords in cls.CONTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > best_score:
                best_score = score
                best_match = doc_type
        
        if best_match and best_score >= 2:
            return best_match, cls.NODE_LABELS.get(best_match, "Document")
        
        # Default to generic Document
        return "Document", "Document"


# =============================================================================
# Reference Extraction
# =============================================================================
class ReferenceExtractor:
    """Extracts references to other entities from document content."""
    
    # Reference patterns
    PATTERNS = {
        "runbook": r"\b(RB|Runbook)[-_](\w+)",
        "sop": r"\b(SOP)[-_](\w+)",
        "faq": r"\b(FAQ)[-_](\w+)",
        "known_issue": r"\b(KI|KnownIssue)[-_](\w+)",
        "service": r"\b(SVC|Service)[-_](\w+)",
        "document": r"\b(DOC|Document)[-_](\w+)",
        "release": r"\b(REL|Release)[-_](\w+)",
    }
    
    @classmethod
    def extract_all(cls, content: str) -> Dict[str, Set[str]]:
        """Extract all references from content."""
        refs = {}
        
        for ref_type, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            # matches = [("RB", "001"), ("Runbook", "Voice_Outage"), ...]
            ids = set()
            for prefix, suffix in matches:
                # Normalize: RB-001 or Runbook-Voice_Outage
                doc_id = f"{prefix.upper()}-{suffix}"
                ids.add(doc_id)
            
            if ids:
                refs[ref_type] = ids
        
        return refs


# =============================================================================
# Keyword Extraction
# =============================================================================
class KeywordExtractor:
    """Extracts keywords for semantic matching."""
    
    # Domain-specific keywords
    CATEGORIES = {
        "voice": ["voice", "call", "voip", "sip", "pstn", "telephony"],
        "chat": ["chat", "messaging", "whatsapp", "sms", "facebook"],
        "routing": ["routing", "queue", "skill", "agent assignment", "overflow"],
        "copilot": ["copilot", "ai", "suggestion", "summarization"],
        "reporting": ["report", "dashboard", "analytics", "kpi", "metrics"],
        "authentication": ["auth", "sso", "login", "session", "oauth"],
        "integration": ["integration", "api", "webhook", "connector"],
        "performance": ["latency", "timeout", "performance", "slow", "degradation"],
        "error": ["error", "exception", "failure", "crash", "bug"],
    }
    
    @classmethod
    def extract(cls, content: str) -> Set[str]:
        """Extract keywords from content."""
        content_lower = content.lower()
        keywords = set()
        
        for category, terms in cls.CATEGORIES.items():
            if any(term in content_lower for term in terms):
                keywords.add(category)
        
        return keywords


# =============================================================================
# Intelligent Edge Inference
# =============================================================================
class EdgeInferenceEngine:
    """
    Infers relationships between documents based on:
    1. Explicit references (KI-001 → RB-002)
    2. Keyword overlap (both mention 'voice' + 'routing')
    3. Naming patterns (KI-Voice-Transfer → Runbook-Voice-Outage)
    """
    
    def __init__(self, kg: KnowledgeGraphService):
        self.kg = kg
        self.documents: List[DocumentMetadata] = []
    
    def add_document(self, doc: DocumentMetadata):
        """Add document for analysis."""
        self.documents.append(doc)
    
    def infer_edges(self) -> List[Dict[str, Any]]:
        """
        Infer edges between all documents.
        
        Returns:
            List of edge dicts: {from_id, to_id, edge_type, confidence, reason}
        """
        edges = []
        
        # 1. Explicit reference edges
        edges.extend(self._infer_explicit_references())
        
        # 2. Keyword-based semantic edges
        edges.extend(self._infer_semantic_edges())
        
        # 3. Naming pattern edges
        edges.extend(self._infer_naming_pattern_edges())
        
        # Deduplicate
        edges = self._deduplicate_edges(edges)
        
        return edges
    
    def _infer_explicit_references(self) -> List[Dict[str, Any]]:
        """Edges from explicit references (KI-001 mentions RB-002)."""
        edges = []
        
        for doc in self.documents:
            refs = ReferenceExtractor.extract_all(doc.content)
            
            for ref_type, ref_ids in refs.items():
                for ref_id in ref_ids:
                    # Determine edge type
                    edge_type = self._get_edge_type_for_reference(
                        doc.doc_type, ref_type, doc.content
                    )
                    
                    edges.append({
                        "from_id": doc.doc_id,
                        "from_label": doc.node_label,
                        "to_id": ref_id,
                        "to_type": ref_type,
                        "edge_type": edge_type,
                        "confidence": 1.0,
                        "reason": f"Explicit reference in {doc.filename}",
                    })
        
        return edges
    
    def _infer_semantic_edges(self) -> List[Dict[str, Any]]:
        """Edges from keyword overlap."""
        edges = []
        threshold = 2  # At least 2 common keywords
        
        for i, doc1 in enumerate(self.documents):
            for doc2 in self.documents[i+1:]:
                common_kw = doc1.keywords & doc2.keywords
                
                if len(common_kw) >= threshold:
                    # Only link certain types
                    if self._should_link_semantically(doc1.doc_type, doc2.doc_type):
                        edges.append({
                            "from_id": doc1.doc_id,
                            "from_label": doc1.node_label,
                            "to_id": doc2.doc_id,
                            "to_label": doc2.node_label,
                            "edge_type": "RELATED_TO",
                            "confidence": min(len(common_kw) / 5.0, 0.95),
                            "reason": f"Shared keywords: {', '.join(common_kw)}",
                        })
        
        return edges
    
    def _infer_naming_pattern_edges(self) -> List[Dict[str, Any]]:
        """Edges from similar naming patterns (KI-Voice-X → RB-Voice-Y)."""
        edges = []
        
        for i, doc1 in enumerate(self.documents):
            for doc2 in self.documents[i+1:]:
                # Extract suffix after type prefix
                suffix1 = self._extract_name_suffix(doc1.doc_id)
                suffix2 = self._extract_name_suffix(doc2.doc_id)
                
                # Check similarity
                similarity = self._name_similarity(suffix1, suffix2)
                
                if similarity > 0.5:
                    edge_type = self._get_edge_type_for_pair(
                        doc1.doc_type, doc2.doc_type
                    )
                    
                    if edge_type:
                        edges.append({
                            "from_id": doc1.doc_id,
                            "from_label": doc1.node_label,
                            "to_id": doc2.doc_id,
                            "to_label": doc2.node_label,
                            "edge_type": edge_type,
                            "confidence": similarity,
                            "reason": f"Name pattern similarity: {similarity:.2f}",
                        })
        
        return edges
    
    def _get_edge_type_for_reference(
        self, from_type: str, to_type: str, content: str
    ) -> str:
        """Determine edge type based on context."""
        content_lower = content.lower()
        
        # Known Issue → Runbook
        if from_type == "KnownIssue" and to_type == "runbook":
            if "workaround" in content_lower or "mitigat" in content_lower:
                return "WORKAROUND_IN"
            return "RESOLVED_BY"
        
        # SOP → Runbook
        if from_type == "SOP" and to_type == "runbook":
            return "HAS_RUNBOOK"
        
        # Known Issue → FAQ
        if from_type == "KnownIssue" and to_type == "faq":
            return "DOCUMENTED_IN"
        
        # UserGuide → FAQ
        if from_type == "UserGuide" and to_type == "faq":
            return "HAS_FAQ"
        
        # Default
        return "RELATED_TO"
    
    def _should_link_semantically(self, type1: str, type2: str) -> bool:
        """Decide if two types should be linked semantically."""
        # Don't link documents of same type
        if type1 == type2:
            return False
        
        # Link Known Issues to Runbooks/FAQs/SOPs
        if type1 == "KnownIssue" and type2 in ["Runbook", "FAQ", "SOP"]:
            return True
        if type2 == "KnownIssue" and type1 in ["Runbook", "FAQ", "SOP"]:
            return True
        
        # Link UserGuides to FAQs
        if (type1 == "UserGuide" and type2 == "FAQ") or \
           (type2 == "UserGuide" and type1 == "FAQ"):
            return True
        
        # Link SOPs to Runbooks
        if (type1 == "SOP" and type2 == "Runbook") or \
           (type2 == "SOP" and type1 == "Runbook"):
            return True
        
        return False
    
    def _get_edge_type_for_pair(self, type1: str, type2: str) -> Optional[str]:
        """Get edge type for a pair of document types."""
        pairs = {
            ("KnownIssue", "Runbook"): "RESOLVED_BY",
            ("KnownIssue", "FAQ"): "DOCUMENTED_IN",
            ("SOP", "Runbook"): "HAS_RUNBOOK",
            ("UserGuide", "FAQ"): "HAS_FAQ",
        }
        
        key = (type1, type2)
        if key in pairs:
            return pairs[key]
        
        # Try reverse
        key_rev = (type2, type1)
        if key_rev in pairs:
            return pairs[key_rev]
        
        return "RELATED_TO"
    
    def _extract_name_suffix(self, doc_id: str) -> str:
        """Extract suffix after type prefix (KI-Voice-Transfer → Voice-Transfer)."""
        parts = doc_id.split("-", 1)
        return parts[1] if len(parts) > 1 else doc_id
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        # Simple token-based similarity
        tokens1 = set(re.findall(r'\w+', name1.lower()))
        tokens2 = set(re.findall(r'\w+', name2.lower()))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
    
    def _deduplicate_edges(self, edges: List[Dict]) -> List[Dict]:
        """Remove duplicate edges, keeping highest confidence."""
        edge_map = {}
        
        for edge in edges:
            key = (edge["from_id"], edge["to_id"], edge["edge_type"])
            
            if key not in edge_map or edge["confidence"] > edge_map[key]["confidence"]:
                edge_map[key] = edge
        
        return list(edge_map.values())


# =============================================================================
# Bulk Import Service
# =============================================================================
class BulkImportService:
    """
    Imports multiple documents from ZIP archive.
    
    Steps:
    1. Extract ZIP
    2. Parse each file
    3. Detect document type
    4. Extract references & keywords
    5. Create nodes in Neo4j
    6. Infer edges
    7. Create edges in Neo4j
    """
    
    def __init__(self, tenant_id: str = "tenant_demo"):
        self.tenant_id = tenant_id
        self.kg = KnowledgeGraphService(tenant_id)
        self.inference_engine = EdgeInferenceEngine(self.kg)
        self.stats = {
            "files_processed": 0,
            "nodes_created": 0,
            "edges_created": 0,
            "errors": [],
        }
    
    def import_from_zip(
        self,
        zip_path: Optional[str] = None,
        zip_bytes: Optional[bytes] = None,
        create_edges: bool = True,
        min_edge_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Import documents from ZIP archive.
        
        Args:
            zip_path: Path to ZIP file
            zip_bytes: ZIP file as bytes (alternative to zip_path)
            create_edges: Whether to infer and create edges
            min_edge_confidence: Minimum confidence for edge creation
        
        Returns:
            Import statistics
        """
        # Load ZIP
        if zip_path:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                files = self._extract_files(zf)
        elif zip_bytes:
            with zipfile.ZipFile(BytesIO(zip_bytes), 'r') as zf:
                files = self._extract_files(zf)
        else:
            raise ValueError("Either zip_path or zip_bytes must be provided")
        
        logger.info(f"Extracted {len(files)} files from ZIP")
        
        # Process each file
        for filename, content in files.items():
            try:
                self._process_document(filename, content)
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
                self.stats["errors"].append({
                    "filename": filename,
                    "error": str(e),
                })
        
        # Infer edges
        if create_edges:
            edges = self.inference_engine.infer_edges()
            
            # Filter by confidence
            edges = [e for e in edges if e["confidence"] >= min_edge_confidence]
            
            logger.info(f"Inferred {len(edges)} edges")
            
            # Create edges in Neo4j
            for edge in edges:
                try:
                    self._create_edge(edge)
                    self.stats["edges_created"] += 1
                except Exception as e:
                    logger.error(f"Error creating edge: {e}")
                    self.stats["errors"].append({
                        "edge": f"{edge['from_id']} -> {edge['to_id']}",
                        "error": str(e),
                    })
        
        return {
            "status": "completed",
            "stats": self.stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _extract_files(self, zf: zipfile.ZipFile) -> Dict[str, str]:
        """Extract text files from ZIP."""
        files = {}
        
        for info in zf.filelist:
            # Skip directories and non-text files
            if info.is_dir():
                continue
            
            ext = Path(info.filename).suffix.lower()
            if ext not in [".txt", ".md", ".markdown"]:
                continue
            
            # Read content
            try:
                content = zf.read(info.filename).decode('utf-8')
                files[info.filename] = content
            except Exception as e:
                logger.warning(f"Skipping {info.filename}: {e}")
        
        return files
    
    def _process_document(self, filename: str, content: str):
        """Process a single document."""
        # Extract filename without path
        base_filename = Path(filename).name
        
        # Detect type
        doc_type, node_label = DocumentTypeDetector.detect(base_filename, content)
        
        # Generate doc_id
        doc_id = self._generate_doc_id(base_filename, doc_type)
        
        # Extract metadata
        doc_meta = DocumentMetadata(
            doc_id=doc_id,
            filename=base_filename,
            title=self._extract_title(content, base_filename),
            doc_type=doc_type,
            node_label=node_label,
            content=content,
            extracted_refs=set(),
            keywords=KeywordExtractor.extract(content),
        )
        
        # Add to inference engine
        self.inference_engine.add_document(doc_meta)
        
        # Create node in Neo4j
        node = self._create_node(doc_meta)
        
        self.stats["files_processed"] += 1
        self.stats["nodes_created"] += 1
        
        logger.info(f"✅ Processed {base_filename} → {doc_type} ({doc_id})")
    
    def _generate_doc_id(self, filename: str, doc_type: str) -> str:
        """Generate unique document ID."""
        # Remove extension
        name = Path(filename).stem
        
        # If already has prefix, use as-is
        for prefix in ["RB-", "KI-", "FAQ-", "SOP-", "SPO-", "DOC-"]:
            if name.startswith(prefix):
                return name
        
        # Generate prefix
        prefix_map = {
            "Runbook": "RB",
            "KnownIssue": "KI",
            "FAQ": "FAQ",
            "SOP": "SOP",
            "SPO": "SPO",
            "UserGuide": "UG",
            "Document": "DOC",
        }
        
        prefix = prefix_map.get(doc_type, "DOC")
        
        # Clean name
        clean_name = re.sub(r'^(Runbook|KnownIssue|FAQ|SOP|SPO|UserGuide|Guide)[-_]', '', name, flags=re.IGNORECASE)
        
        return f"{prefix}-{clean_name}"
    
    def _extract_title(self, content: str, filename: str) -> str:
        """Extract title from content or filename."""
        # Try to find title in first few lines
        lines = content.split('\n')[:10]
        
        for line in lines:
            # Markdown heading
            if line.startswith('#'):
                return line.lstrip('#').strip()
            
            # Title line (all caps or followed by ===)
            if line.isupper() and 10 < len(line) < 100:
                return line.strip()
        
        # Fallback to filename
        return Path(filename).stem.replace('_', ' ').replace('-', ' ').title()
    
    def _create_node(self, doc: DocumentMetadata) -> Dict[str, Any]:
        """Create node in Neo4j based on document type."""
        if doc.node_label == "Runbook":
            return self._create_runbook(doc)
        elif doc.node_label == "FAQ":
            return self._create_faq(doc)
        elif doc.node_label == "SOP":
            return self._create_sop(doc)
        elif doc.node_label == "KnownIssue":
            return self._create_known_issue(doc)
        else:
            return self._create_document(doc)
    
    def _create_runbook(self, doc: DocumentMetadata) -> Dict[str, Any]:
        """Create Runbook node."""
        runbook = RunbookNode(
            tenant_id=self.tenant_id,
            runbook_id=doc.doc_id.lower(),
            title=doc.title,
            description=self._extract_description(doc.content),
            type=RunbookType.diagnostic,  # Default
            steps=self._extract_steps(doc.content),
            success_rate=0.0,
            times_used=0,
        )
        
        return self.kg.create_node("Runbook", runbook)
    
    def _create_faq(self, doc: DocumentMetadata) -> Dict[str, Any]:
        """Create FAQ node."""
        question, answer = self._extract_qa(doc.content)
        
        faq = FAQNode(
            tenant_id=self.tenant_id,
            faq_id=doc.doc_id.lower(),
            question=question or doc.title,
            answer=answer or doc.content[:500],
            category="general",
            helpful_votes=0,
        )
        
        return self.kg.create_node("FAQ", faq)
    
    def _create_sop(self, doc: DocumentMetadata) -> Dict[str, Any]:
        """Create SOP node."""
        sop = SOPNode(
            tenant_id=self.tenant_id,
            sop_id=doc.doc_id.lower(),
            title=doc.title,
            description=self._extract_description(doc.content),
            category=SOPCategory.incident_response,  # Default
            status="active",
            approval_required=False,
        )
        
        return self.kg.create_node("SOP", sop)
    
    def _create_known_issue(self, doc: DocumentMetadata) -> Dict[str, Any]:
        """Create Known Issue node."""
        known_issue = KnownIssueNode(
            tenant_id=self.tenant_id,
            issue_id=doc.doc_id.lower(),
            title=doc.title,
            description=self._extract_description(doc.content),
            severity=KnownIssueSeverity.P2,  # Default
            status=KnownIssueStatus.open,
            workaround_summary=self._extract_workaround(doc.content),
            workaround_steps=self._extract_steps(doc.content),
            affected_entities=[],
        )
        
        return self.kg.add_known_issue(known_issue)
    
    def _create_document(self, doc: DocumentMetadata) -> Dict[str, Any]:
        """Create generic Document node."""
        document = DocumentNode(
            tenant_id=self.tenant_id,
            doc_id=doc.doc_id.lower(),
            title=doc.title,
            type=DocumentType.guide if doc.doc_type == "UserGuide" else DocumentType.reference,
            source=DocumentSource.internal,
            url=f"file://{doc.filename}",
            content_summary=doc.content[:200],
            tags=list(doc.keywords),
        )
        
        return self.kg.create_node("Document", document)
    
    def _create_edge(self, edge: Dict[str, Any]):
        """Create edge in Neo4j."""
        # Use EdgeFactory or direct Cypher
        query = """
        MATCH (a {tenant_id: $tenant_id})
        WHERE (a.runbook_id = $from_id OR a.faq_id = $from_id OR a.sop_id = $from_id 
               OR a.issue_id = $from_id OR a.doc_id = $from_id)
        
        MATCH (b {tenant_id: $tenant_id})
        WHERE (b.runbook_id = $to_id OR b.faq_id = $to_id OR b.sop_id = $to_id 
               OR b.issue_id = $to_id OR b.doc_id = $to_id)
        
        MERGE (a)-[r:%s {
            tenant_id: $tenant_id,
            confidence: $confidence,
            reason: $reason,
            created_at: datetime()
        }]->(b)
        
        RETURN r
        """ % edge["edge_type"]
        
        params = {
            "tenant_id": self.tenant_id,
            "from_id": edge["from_id"].lower(),
            "to_id": edge.get("to_id", "").lower(),
            "confidence": edge["confidence"],
            "reason": edge["reason"],
        }
        
        self.kg.execute_query(query, params)
    
    # Helper methods for text extraction
    
    def _extract_description(self, content: str) -> str:
        """Extract description from content."""
        # Take first paragraph
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50 and not para.startswith('#'):
                return para[:500]
        return content[:200]
    
    def _extract_steps(self, content: str) -> List[str]:
        """Extract numbered steps from content."""
        steps = []
        
        # Pattern: "1. Step one" or "Step 1: Do this"
        patterns = [
            r'^\d+\.\s+(.+)$',
            r'^Step\s+\d+:\s*(.+)$',
            r'^-\s+(.+)$',  # Bullet points
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    steps.append(match.group(1))
                    break
        
        return steps[:20]  # Limit to 20 steps
    
    def _extract_qa(self, content: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract question and answer from FAQ content."""
        question = None
        answer = None
        
        # Pattern: "Question: ...\nAnswer: ..."
        q_match = re.search(r'Question:\s*(.+?)(?=\n|$)', content, re.IGNORECASE)
        a_match = re.search(r'Answer:\s*(.+?)(?=\n\n|$)', content, re.IGNORECASE | re.DOTALL)
        
        if q_match:
            question = q_match.group(1).strip()
        if a_match:
            answer = a_match.group(1).strip()
        
        return question, answer
    
    def _extract_workaround(self, content: str) -> Optional[str]:
        """Extract workaround summary."""
        match = re.search(
            r'Workaround:\s*(.+?)(?=\n\n|$)',
            content,
            re.IGNORECASE | re.DOTALL
        )
        
        if match:
            return match.group(1).strip()[:500]
        
        return None


# =============================================================================
# Convenience Functions
# =============================================================================
def import_documents_from_zip(
    zip_path: str,
    tenant_id: str = "tenant_demo",
    create_edges: bool = True,
    min_edge_confidence: float = 0.5,
) -> Dict[str, Any]:
    """
    Convenience function to import documents from ZIP.
    
    Usage:
        result = import_documents_from_zip("docs.zip")
        print(result["stats"])
    """
    service = BulkImportService(tenant_id)
    return service.import_from_zip(
        zip_path=zip_path,
        create_edges=create_edges,
        min_edge_confidence=min_edge_confidence,
    )

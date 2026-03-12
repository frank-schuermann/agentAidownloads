# scripts/kg_seed_docs_minimal.py
from __future__ import annotations

import json
from datetime import datetime, timezone

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.models.nodes import DocumentNode, FAQNode

TENANT_ID = "tenant_demo"


def main() -> None:
    kg = KnowledgeGraphService(TENANT_ID)

    doc = DocumentNode(
        tenant_id=TENANT_ID,
        doc_id="doc_payment_oncall_guide",
        title="Payment Service On-Call Guide",
        type="wiki",
        source="internal",
        url="https://internal/wiki/payment-oncall",
        author="SRE Platform",
        last_updated=datetime(2026, 2, 5, tzinfo=timezone.utc),
        tags=["payment", "oncall", "5xx", "timeout", "checkout"],
        content_summary="Dashboards, common failure modes, and quick triage steps for Payment Service incidents.",
    )

    seed_doc = kg.add_document(
        doc=doc,
        service_ids=["svc_payment"],
        product_ids=["prod_001"],   # optional (you seeded this)
        feature_ids=["feat_001"],   # optional (you seeded this)
    )

    faq = FAQNode(
        tenant_id=TENANT_ID,
        faq_id="faq_payment_5xx_debug",
        question="How do I debug a sudden 5xx spike in Payment?",
        answer="Check payment error dashboards, verify DB latency/connection pool, and consider rolling restart if safe.",
        category="payment",
        helpful_votes=12,
    )

    seed_faq = kg.add_faq(
        faq=faq,
        related_symptoms=["scenario::5xx_spike", "scenario::timeout_surge"],
    )

    print("Seed Docs result:")
    print(json.dumps({"document": seed_doc, "faq": seed_faq}, indent=2))


if __name__ == "__main__":
    main()
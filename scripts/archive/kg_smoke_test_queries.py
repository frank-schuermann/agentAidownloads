# scripts/kg_smoke_test_queries.py
import os
import json

from core.knowledge_graph.db import get_graph_db
from core.knowledge_graph.service import KnowledgeGraphService


def main():
    tenant_id = os.getenv("TENANT_ID", "tenant_demo")

    db = get_graph_db()
    print("Neo4j health:", db.health_check())
    if not db.health_check():
        print("Neo4j down - cannot run smoke tests.")
        return

    kg = KnowledgeGraphService(tenant_id=tenant_id)

    blast = kg.get_blast_radius("svc_db_cluster", depth=3)
    print("\nBlast radius for svc_db_cluster:\n", json.dumps(blast, indent=2))


if __name__ == "__main__":
    main()

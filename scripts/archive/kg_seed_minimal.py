# scripts/kg_seed_minimal.py
import os
import json

from core.knowledge_graph.schema import init_graph_db
from core.knowledge_graph.service import KnowledgeGraphService


def main():
    tenant_id = os.getenv("TENANT_ID", "tenant_demo")

    ok = init_graph_db()
    if not ok:
        print("Neo4j not reachable. Seed skipped.")
        return

    kg = KnowledgeGraphService(tenant_id=tenant_id)

    services = [
        {
            "service_id": "svc_api_gateway",
            "name": "API Gateway",
            "owner_team": "Platform",
            "depends_on": [
                {"service_id": "svc_auth", "dependency_type": "http", "is_critical": True, "weight": 0.9},
                {"service_id": "svc_payment", "dependency_type": "http", "is_critical": True, "weight": 0.9},
            ],
        },
        {
            "service_id": "svc_auth",
            "name": "Auth Service",
            "owner_team": "Platform",
            "depends_on": [{"service_id": "svc_db_cluster", "dependency_type": "database", "is_critical": True}],
        },
        {
            "service_id": "svc_payment",
            "name": "Payment Service",
            "owner_team": "Platform",
            "depends_on": [{"service_id": "svc_db_cluster", "dependency_type": "database", "is_critical": True}],
        },
        {
            "service_id": "svc_db_cluster",
            "name": "Database Cluster",
            "owner_team": "Data",
            "depends_on": [],
        },
    ]

    out = kg.ingest_services(services)
    print("Seed result:\n", json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

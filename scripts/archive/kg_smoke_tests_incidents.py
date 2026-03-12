# scripts/kg_smoke_test_incidents.py
from __future__ import annotations

import json
from core.knowledge_graph.service import KnowledgeGraphService

TENANT_ID = "tenant_demo"


def main() -> None:
    kg = KnowledgeGraphService(TENANT_ID)

    print("\nIncident history for svc_payment:")
    history = kg.get_incident_history("svc_payment", limit=10)
    print(json.dumps(history, indent=2))

    print("\nSimilar incidents for symptoms=[5xx_spike, timeout_surge] on svc_payment:")
    sims = kg.find_similar_incidents(
        symptoms=["5xx_spike", "timeout_surge"],
        affected_service="svc_payment",
        limit=5,
    )
    print(json.dumps(sims, indent=2))

    print("\nMost effective resolution for symptom_type=5xx_spike (before updates):")
    best = kg.get_most_effective_resolution("5xx_spike")
    print(json.dumps(best, indent=2))

    print("\nUpdate resolution effectiveness: res_2026_100 success=True x2, then failure x1")
    kg.update_resolution_effectiveness("res_2026_100", success=True)
    kg.update_resolution_effectiveness("res_2026_100", success=True)
    kg.update_resolution_effectiveness("res_2026_100", success=False)

    print("\nMost effective resolution for symptom_type=5xx_spike (after updates):")
    best2 = kg.get_most_effective_resolution("5xx_spike")
    print(json.dumps(best2, indent=2))


if __name__ == "__main__":
    main()

# scripts/kg_seed_incidents_minimal.py
from __future__ import annotations

import json
from datetime import datetime, timezone

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.models.nodes import (
    IncidentNode,
    RootCauseNode,
    SymptomNode,
    ResolutionNode,
)

TENANT_ID = "tenant_demo"


def seed_incidents_minimal() -> dict:
    kg = KnowledgeGraphService(TENANT_ID)

    # Incident A
    inc_a = IncidentNode(
        tenant_id=TENANT_ID,
        incident_id="inc_2026_100",
        title="Payment checkout 5xx spike",
        severity="P1",
        status="resolved",
        root_cause_category="infrastructure",
        summary="DB failover caused transient connection resets",
        started_at=datetime(2026, 2, 10, 2, 15, tzinfo=timezone.utc),
        resolved_at=datetime(2026, 2, 10, 2, 45, tzinfo=timezone.utc),
        affected_services=["svc_payment"],
    )

    rc_a = RootCauseNode(
        tenant_id=TENANT_ID,
        root_cause_id="rc_db_failover",
        category="infrastructure",
        description="DB failover misconfigured timeouts",
        avg_confidence=0.8,
        prevention_measures=["Tune connection timeouts", "Add failover tests"],
    )

    symptoms_a = [
        SymptomNode(
            tenant_id=TENANT_ID,
            symptom_id="sym_2026_100_1",
            type="5xx_spike",
            description="5xx spike on /checkout",
            affected_service="svc_payment",
            frequency=15,
        ),
        SymptomNode(
            tenant_id=TENANT_ID,
            symptom_id="sym_2026_100_2",
            type="timeout_surge",
            description="Timeout surge on payment capture",
            affected_service="svc_payment",
            frequency=9,
        ),
    ]

    res_a = ResolutionNode(
        tenant_id=TENANT_ID,
        resolution_id="res_2026_100",
        type="config_change",
        description="Adjusted DB connection timeout + restarted payment pods",
        steps=["Update config", "Rolling restart", "Verify error rate"],
        effectiveness_score=0.0,  # will be updated by update_resolution_effectiveness()
        success_count=0,
        failure_count=0,
    )

    kg.record_incident(
        incident=inc_a,
        root_causes=[rc_a],
        symptoms=symptoms_a,
        resolution=res_a,
        affected_service_ids=["svc_payment"],
    )

    # Incident B (same symptoms -> should SIMILAR_TO with high score)
    inc_b = IncidentNode(
        tenant_id=TENANT_ID,
        incident_id="inc_2026_101",
        title="Payment timeout surge + 5xx",
        severity="P1",
        status="resolved",
        root_cause_category="infrastructure",
        summary="Similar pattern observed after regional DB instability",
        started_at=datetime(2026, 2, 12, 3, 5, tzinfo=timezone.utc),
        resolved_at=datetime(2026, 2, 12, 3, 40, tzinfo=timezone.utc),
        affected_services=["svc_payment"],
    )

    rc_b = RootCauseNode(
        tenant_id=TENANT_ID,
        root_cause_id="rc_db_failover",  # same root cause id -> should bump frequency
        category="infrastructure",
        description="DB failover misconfigured timeouts",
        avg_confidence=0.78,
        prevention_measures=["Tune connection timeouts", "Chaos failover drills"],
    )

    # same symptom TYPES as incident A -> similarity should be 1.0
    symptoms_b = [
        SymptomNode(
            tenant_id=TENANT_ID,
            symptom_id="sym_2026_101_1",
            type="5xx_spike",
            description="5xx spike on /checkout",
            affected_service="svc_payment",
            frequency=12,
        ),
        SymptomNode(
            tenant_id=TENANT_ID,
            symptom_id="sym_2026_101_2",
            type="timeout_surge",
            description="Timeout surge on payment capture",
            affected_service="svc_payment",
            frequency=7,
        ),
    ]

    res_b = ResolutionNode(
        tenant_id=TENANT_ID,
        resolution_id="res_2026_101",
        type="restart",
        description="Restarted pods and stabilized DB connections",
        steps=["Restart payment deployment", "Verify metrics"],
        effectiveness_score=0.0,
        success_count=0,
        failure_count=0,
    )

    kg.record_incident(
        incident=inc_b,
        root_causes=[rc_b],
        symptoms=symptoms_b,
        resolution=res_b,
        affected_service_ids=["svc_payment"],
    )

    return {"ok": True, "seeded": ["inc_2026_100", "inc_2026_101"]}


if __name__ == "__main__":
    out = seed_incidents_minimal()
    print(json.dumps(out, indent=2))

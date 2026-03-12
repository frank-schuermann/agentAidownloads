# scripts/kg_seed_sop_minimal.py
from __future__ import annotations

import json
from datetime import datetime, timezone

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.models.nodes import SOPNode, SOPStepNode

TENANT_ID = "tenant_demo"


def main() -> None:
    kg = KnowledgeGraphService(TENANT_ID)

    sop = SOPNode(
        tenant_id=TENANT_ID,
        sop_id="sop_p1_payment_5xx",
        title="P1 Payment 5xx Spike Response",
        version="1.0",
        category="incident_response",
        status="active",
        owner_team="Platform",
        approval_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
        review_due_date=datetime(2026, 8, 1, tzinfo=timezone.utc),
        last_reviewed=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    steps = [
        SOPStepNode(
            tenant_id=TENANT_ID,
            step_id="sop_p1_payment_5xx_step_1",
            sop_id=sop.sop_id,
            order=1,
            instruction="Confirm elevated 5xx on /checkout and verify customer impact.",
            expected_outcome="Validated incident scope and initial metrics snapshot.",
            requires_approval=False,
            role_required="L2",
            commands=["kubectl logs deploy/payment --tail=200", "grafana: payment-5xx-dashboard"],
        ),
        SOPStepNode(
            tenant_id=TENANT_ID,
            step_id="sop_p1_payment_5xx_step_2",
            sop_id=sop.sop_id,
            order=2,
            instruction="Check downstream DB latency and connection saturation.",
            expected_outcome="Determine if DB is contributing to 5xx spike.",
            requires_approval=False,
            role_required="L2",
            commands=["kubectl top pods -n payments", "db-admin: check connection pool"],
        ),
        SOPStepNode(
            tenant_id=TENANT_ID,
            step_id="sop_p1_payment_5xx_step_3",
            sop_id=sop.sop_id,
            order=3,
            instruction="If DB issue suspected, page Data team and initiate war-room.",
            expected_outcome="Correct team engaged and coordinated response.",
            requires_approval=False,
            role_required="IncidentCommander",
            commands=["page Data on-call", "start war-room bridge"],
        ),
        SOPStepNode(
            tenant_id=TENANT_ID,
            step_id="sop_p1_payment_5xx_step_4",
            sop_id=sop.sop_id,
            order=4,
            instruction="Apply mitigation: restart payment pods OR adjust DB timeout config (as approved).",
            expected_outcome="5xx rate returns to baseline within 10 minutes.",
            requires_approval=True,
            role_required="L3",
            commands=["kubectl rollout restart deploy/payment", "apply config change (approved)"],
        ),
        SOPStepNode(
            tenant_id=TENANT_ID,
            step_id="sop_p1_payment_5xx_step_5",
            sop_id=sop.sop_id,
            order=5,
            instruction="Send customer comms update if enterprise/VIP impacted; update incident ticket timeline.",
            expected_outcome="Stakeholders informed, timeline complete.",
            requires_approval=False,
            role_required="Comms",
            commands=["notify customer contacts", "update incident ticket"],
        ),
    ]

    out = kg.add_sop(
        sop=sop,
        steps=steps,
        applicable_services=["svc_payment"],
        applicable_scenarios=["5xx_spike"],
    )

    print("Seed SOP result:")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

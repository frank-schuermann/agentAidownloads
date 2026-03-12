# scripts/kg_seed_runbooks_minimal.py
from __future__ import annotations

import json
from datetime import datetime, timezone

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.models.nodes import (
    RunbookNode,
    KnownWorkaroundNode,
    RootCauseNode,
)

TENANT_ID = "tenant_demo"


def main() -> None:
    kg = KnowledgeGraphService(TENANT_ID)

    # -------------------------
    # 1) Seed a RootCause (so workaround linking works)
    # -------------------------
    root_cause = RootCauseNode(
        tenant_id=TENANT_ID,
        root_cause_id="rc_infra_demo",
        category="infrastructure",
        description="Demo infrastructure instability used for seeding workarounds.",
        frequency=1,
        avg_confidence=0.7,
        recommended_fix="Stabilize DB connectivity and tune timeouts.",
        prevention_measures=[
            "Improve DB failover tests",
            "Add connection pool saturation alerts",
            "Validate timeouts during peak traffic",
        ],
    )

    # Your create_node() merges based on unique keys, so this is idempotent.
    kg.create_node("RootCause", root_cause)

    # -------------------------
    # 2) Seed a Runbook
    # -------------------------
    runbook = RunbookNode(
        tenant_id=TENANT_ID,
        runbook_id="rb_payment_5xx_timeout_triage",
        title="Payment 5xx + Timeout Triage",
        description="Triage and remediate payment 5xx spikes and timeout surges.",
        type="remediation",
        steps=[
            "Check payment error dashboards and confirm spike",
            "Check DB latency/connection pool saturation",
            "Restart payment pods if safe",
            "Adjust DB timeouts if needed (approved)",
            "Verify recovery and document timeline",
        ],
        success_rate=0.0,
        times_used=0,
        last_used=None,
        last_updated=datetime(2026, 2, 1, tzinfo=timezone.utc),
        author="SRE Platform",
    )

    seed_runbook = kg.add_runbook(
        runbook=runbook,
        applicable_services=["svc_payment"],
        applicable_symptoms=["5xx_spike", "timeout_surge"],
    )

    # -------------------------
    # 3) Seed a Known Workaround linked to that RootCause
    # -------------------------
    workaround = KnownWorkaroundNode(
        tenant_id=TENANT_ID,
        workaround_id="wa_infra_conn_pool_temp",
        description="Temporarily increase DB connection pool + reduce keepalive to stabilize traffic.",
        steps=[
            "Increase pool size by 20%",
            "Reduce keepalive timeout by 30%",
            "Monitor error rate and DB saturation",
            "Rollback to baseline after incident",
        ],
        risk_level="medium",
        temporary=True,
        expiry_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )

    seed_workaround = kg.add_workaround(
        workaround=workaround,
        root_cause_id="rc_infra_demo",
    )

    print("Seed Runbook result:")
    print(
        json.dumps(
            {"root_cause_id": root_cause.root_cause_id, "runbook": seed_runbook, "workaround": seed_workaround},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
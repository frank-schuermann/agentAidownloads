# scripts/kg_seed_business_minimal.py
from __future__ import annotations

import json

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.models.nodes import (
    CustomerContactNode,
    CustomerNode,
    FeatureNode,
    ProductNode,
    SLAContractNode,
)

TENANT_ID = "tenant_demo"


def seed_business_minimal() -> dict:
    kg = KnowledgeGraphService(TENANT_ID)

    # -------------------------
    # Subgraph 5: Customer + SLA + Contact
    # -------------------------
    customer = CustomerNode(
        tenant_id=TENANT_ID,
        customer_id="cust_001",
        name="Acme Corp",
        tier="enterprise",
        status="active",
        region="US",
        industry="Media",
        vip=True,
        revenue_impact_per_hour=12000.0,
    )

    sla = SLAContractNode(
        tenant_id=TENANT_ID,
        sla_id="sla_001",
        customer_id="cust_001",
        availability_target=99.9,
        response_time_sla={"P0": 15, "P1": 30, "P2": 60, "P3": 240, "P4": 1440},
        penalty_clause="Credit 10% monthly fee per breach",
        contract_end_date=None,
    )

    contact = CustomerContactNode(
        tenant_id=TENANT_ID,
        contact_id="ct_001",
        name="Jane Doe",
        role="executive",
        email="jane@acme.com",
        phone="+1-555-0100",
        escalation_level=4,
        preferred_channel="phone",
    )

    # Nodes (idempotent MERGE in create_node)
    kg.create_node("Customer", customer)
    kg.create_node("SLAContract", sla)
    kg.create_node("CustomerContact", contact)

    # Edges (use your create_edge signature: *_id_field + *_id_value)
    # Customer -> Service
    kg.create_edge(
        source_label="Customer",
        source_id_field="customer_id",
        source_id_value="cust_001",
        target_label="Service",
        target_id_field="service_id",
        target_id_value="svc_payment",
        relationship="USES_SERVICE",
        properties={"tenant_id": TENANT_ID, "usage_level": "heavy", "custom_config": "default"},
    )

    # Customer -> SLAContract
    kg.create_edge(
        source_label="Customer",
        source_id_field="customer_id",
        source_id_value="cust_001",
        target_label="SLAContract",
        target_id_field="sla_id",
        target_id_value="sla_001",
        relationship="HAS_SLA",
        properties={"tenant_id": TENANT_ID},
    )

    # Customer -> CustomerContact
    kg.create_edge(
        source_label="Customer",
        source_id_field="customer_id",
        source_id_value="cust_001",
        target_label="CustomerContact",
        target_id_field="contact_id",
        target_id_value="ct_001",
        relationship="HAS_CONTACT",
        properties={"tenant_id": TENANT_ID},
    )

    # -------------------------
    # Subgraph 6: Product + Feature + Service mapping
    # -------------------------
    product = ProductNode(
        tenant_id=TENANT_ID,
        product_id="prod_001",
        name="News Platform",
        description="Core news publishing and monetization platform",
        business_owner="VP Product",
        lifecycle_stage="ga",
        revenue_contribution=5000.0,
    )

    feature = FeatureNode(
        tenant_id=TENANT_ID,
        feature_id="feat_001",
        name="Checkout",
        product_id="prod_001",
        status="active",
        flag_name=None,
        launch_date=None,
        owner_team="Platform",
    )

    kg.create_node("Product", product)
    kg.create_node("Feature", feature)

    # Feature -> Product
    kg.create_edge(
        source_label="Feature",
        source_id_field="feature_id",
        source_id_value="feat_001",
        target_label="Product",
        target_id_field="product_id",
        target_id_value="prod_001",
        relationship="PART_OF",
        properties={"tenant_id": TENANT_ID},
    )

    # Feature -> Service
    kg.create_edge(
        source_label="Feature",
        source_id_field="feature_id",
        source_id_value="feat_001",
        target_label="Service",
        target_id_field="service_id",
        target_id_value="svc_payment",
        relationship="POWERED_BY",
        properties={"tenant_id": TENANT_ID, "is_critical_path": True},
    )

    return {
        "tenant_id": TENANT_ID,
        "nodes_merged": ["Customer", "SLAContract", "CustomerContact", "Product", "Feature"],
        "edges_merged": ["USES_SERVICE", "HAS_SLA", "HAS_CONTACT", "PART_OF", "POWERED_BY"],
        "service_used": "svc_payment",
        "customer_id": "cust_001",
        "sla_id": "sla_001",
        "contact_id": "ct_001",
        "product_id": "prod_001",
        "feature_id": "feat_001",
    }


if __name__ == "__main__":
    result = seed_business_minimal()
    print("Seed business minimal result:\n", json.dumps(result, indent=2))

import json
from pathlib import Path

TENANT = "tenant_demo"

kg_delta = {
  "metadata": {
    "graph_name": "Microsoft CCaaS — Support AI Knowledge Graph (Demo Delta)",
    "version": "2.0.0-delta",
    "description": "Delta file containing two new demo scenarios (KI-015, KI-016) to be seeded alongside existing graph.",
    "created_date": "2026-03-05",
    "last_updated": "2026-03-05",
    "schema_version": "v2"
  },
  "node_types": [
    "Service","KnownIssue","Runbook","SOP","Incident","Expert","Customer","Infrastructure","Configuration","FAQ"
  ],
  "edge_types": [
    "HAS_KNOWN_ISSUE","HAS_RUNBOOK","HAS_SOP","WORKAROUND_IN","CONFIGURED_BY","RUNS_ON",
    "REPORTED_INCIDENT","IMPACTED_BY","RESOLVED_BY","ASSIGNED_TO","HAS_FAQ","DOCUMENTED_IN"
  ],
  "nodes": [
    # -----------------------------
    # Scenario 15 — SSO login failures
    # -----------------------------
    {
      "id": "SVC-015",
      "type": "Service",
      "label": "Identity & Authentication Gateway",
      "properties": {
        "service_id": "SVC-015",
        "tenant_id": TENANT,
        "criticality": "P1",
        "sla_uptime": "99.95%",
        "status": "Active",
        "technology_stack": ["Azure AD (Entra ID)","SAML","OAuth2/OIDC","Dataverse","API Gateway"],
        "description": "SSO entrypoint for agent/supervisor login. Validates SAML/OIDC tokens and issues session cookies/tokens used by Agent Desktop."
      },
      "tags": ["Auth","SSO","SAML","Login"]
    },
    {
      "id": "KI-015",
      "type": "KnownIssue",
      "label": "SSO login failures (SAML login loop / invalid session)",
      "properties": {
        "issue_id": "KI-015",
        "tenant_id": TENANT,
        "severity": "P1",
        "status": "Workaround Available",
        "affected_versions": ["2025 Wave 2"],
        "symptoms": [
          "Agent redirected back to login after successful IdP authentication",
          "SAML assertion rejected intermittently (expired / not-yet-valid)",
          "Spike in sign-in failures during shift start"
        ],
        "root_cause": "Clock drift and strict timestamp validation in the auth gateway when SAML assertions are issued near boundary; tolerance config too low for some regions.",
        "workaround": "Temporarily increase SAML clock-skew tolerance and ensure NTP sync on auth nodes; rolling restart auth gateway if needed.",
        "eta_fix": "2026-04-05",
        "document": "data/KnownIssue_SSO_LoginFailures.txt"
      },
      "tags": ["SSO","SAML","Login","P1"]
    },
    {
      "id": "RB-015",
      "type": "Runbook",
      "label": "SSO Login Loop Recovery (SAML Clock Skew)",
      "properties": {
        "runbook_id": "RB-015",
        "tenant_id": TENANT,
        "category": "Incident Recovery",
        "estimated_time": "25 minutes",
        "steps": [
          "1. Confirm impact: check sign-in failure rate + agent complaints",
          "2. Auth gateway logs: look for SAML_ASSERTION_EXPIRED / ASSERTION_NOT_YET_VALID",
          "3. Verify NTP: confirm clock drift on auth nodes < 30s",
          "4. Temporarily increase SAML clock-skew tolerance (e.g., 2m → 5m)",
          "5. Rolling restart auth gateway nodes (if failures persist)",
          "6. Validate: 10 test logins across regions + monitor error rate 10 mins",
          "7. Revert tolerance to baseline after stability confirmed; document change"
        ],
        "document": "data/Runbook_SSO_SAML_ClockSkew_Recovery.txt"
      },
      "tags": ["SSO","Runbook","SAML","Recovery"]
    },
    {
      "id": "SOP-015",
      "type": "SOP",
      "label": "P1 Communications — SSO Login Failures",
      "properties": {
        "sop_id": "SOP-015",
        "tenant_id": TENANT,
        "category": "Escalation",
        "steps": [
          "1. Confirm scope (tenant/region/queues) and timestamp of onset",
          "2. Notify supervisors: login issues; provide workaround ETA and workaround steps",
          "3. Post updates every 15 minutes until stabilized",
          "4. If >30 mins or >50 agents impacted: page Identity on-call; open vendor ticket if needed",
          "5. After recovery: share summary + mitigation and prevention action"
        ],
        "document": "data/SOP_SSO_P1_Comms.txt"
      },
      "tags": ["SSO","SOP","P1","Comms"]
    },
    {
      "id": "CFG-015",
      "type": "Configuration",
      "label": "SSO / SAML Validation Settings",
      "properties": {
        "flag_id": "CFG-015",
        "tenant_id": TENANT,
        "config_area": "Authentication",
        "admin_path": "Dynamics 365 admin center > Security > Authentication (SSO)",
        "key_settings": [
          "SAML clock-skew tolerance",
          "Assertion audience validation",
          "Token/session TTL",
          "Regional failover policy"
        ]
      },
      "tags": ["SSO","SAML","Config"]
    },
    {
      "id": "FAQ-015",
      "type": "FAQ",
      "label": "Why do I keep getting redirected back to login after SSO?",
      "properties": {
        "faq_id": "FAQ-015",
        "tenant_id": TENANT,
        "question": "After authenticating with SSO, why am I redirected back to the login page?",
        "answer": "This typically occurs when the auth gateway rejects the SAML assertion due to timestamp validation (clock skew) or strict validation settings. Verify NTP, increase skew tolerance temporarily, and follow the SSO login loop recovery runbook."
      },
      "tags": ["SSO","FAQ","Login"]
    },
    {
      "id": "INFRA-015",
      "type": "Infrastructure",
      "label": "Auth Gateway Cluster",
      "properties": {
        "deployment_id": "INFRA-015",
        "tenant_id": TENANT,
        "resource_type": "Azure",
        "regions": ["US East","EU West"],
        "description": "Gateway cluster validating SAML/OIDC tokens and issuing session tokens for Agent Desktop.",
        "monitoring": "Application Insights + Azure Monitor"
      },
      "tags": ["Auth","Gateway","Infra"]
    },
    {
      "id": "INC-015",
      "type": "Incident",
      "label": "INC-20260304: SSO login failures during shift start",
      "properties": {
        "incident_id": "INC-015",
        "tenant_id": TENANT,
        "date": "2026-03-04",
        "severity": "P1",
        "duration": "38 minutes",
        "affected_service": "Identity & Authentication Gateway",
        "affected_customers": ["Enterprise Bank Support Operations"],
        "root_cause": "SAML timestamp validation failures due to clock drift and low skew tolerance.",
        "resolution": "Increased skew tolerance temporarily; ensured NTP sync; rolled auth gateway nodes.",
        "post_mortem": "Add drift alerting; adjust tolerance defaults for multi-region tenants; add canary login tests."
      },
      "tags": ["SSO","Incident","P1"]
    },
    {
      "id": "EXP-015",
      "type": "Expert",
      "label": "Identity Platform On-Call",
      "properties": {
        "employee_id": "EXP-015",
        "role": "SRE (Identity Platform)",
        "expertise": ["SSO","SAML","OAuth","Auth Gateway","NTP/Time Sync"],
        "email": "platform-identity-oncall@hcltech.com",
        "on_call": True,
        "location": "Noida, India"
      },
      "tags": ["SSO","On-Call","Identity"]
    },
    {
      "id": "CUST-015",
      "type": "Customer",
      "label": "Enterprise Bank Support Operations",
      "properties": {
        "customer_id": "CUST-015",
        "tenant_id": TENANT,
        "industry": "Financial Services",
        "agents_licensed": 420,
        "license_type": "Enterprise",
        "sla_tier": "Premier",
        "channels": ["Voice","Chat","Email"],
        "region": "US East",
        "csm": "Rebecca Torres"
      },
      "tags": ["Enterprise","Finance","Premier"]
    },

    # --------------------------------------------
    # Scenario 16 — Copilot hallucination summaries
    # --------------------------------------------
    {
      "id": "SVC-016",
      "type": "Service",
      "label": "Copilot Conversation Intelligence",
      "properties": {
        "service_id": "SVC-016",
        "tenant_id": TENANT,
        "criticality": "P2",
        "sla_uptime": "99.90%",
        "status": "Active",
        "technology_stack": ["Azure OpenAI","Dataverse","Transcript Streaming","Inference Workers"],
        "description": "Generates conversation summaries and coaching insights from finalized transcripts and interaction metadata."
      },
      "tags": ["Copilot","Summaries","LLM","AI"]
    },
    {
      "id": "KI-016",
      "type": "KnownIssue",
      "label": "Copilot hallucination in conversation summaries",
      "properties": {
        "issue_id": "KI-016",
        "tenant_id": TENANT,
        "severity": "P2",
        "status": "Workaround Available",
        "affected_versions": ["2025 Wave 2"],
        "symptoms": [
          "Summary includes actions that did not occur in the call/chat",
          "Incorrect next steps fabricated when transcript is incomplete",
          "Hallucinations correlate with transcript ingestion latency spikes"
        ],
        "root_cause": "Summarization triggered before transcript finalization (ingestion latency/backlog), causing missing context; model fills gaps with plausible but incorrect details.",
        "workaround": "Disable auto-summary for impacted queues/tenants and stabilize transcript ingestion backlog; re-enable only when finalized transcript flag is reliable.",
        "eta_fix": "2026-04-12",
        "document": "data/KnownIssue_Copilot_SummaryHallucination.txt"
      },
      "tags": ["Copilot","Hallucination","Summaries","P2"]
    },
    {
      "id": "RB-016",
      "type": "Runbook",
      "label": "Copilot Summary Accuracy Recovery (Transcript Finalization)",
      "properties": {
        "runbook_id": "RB-016",
        "tenant_id": TENANT,
        "category": "Incident Recovery",
        "estimated_time": "30 minutes",
        "steps": [
          "1. Validate issue: compare transcript vs summary for 5 samples",
          "2. Check transcript ingestion backlog and p95 latency",
          "3. Confirm transcript completeness/finalized flags are being set",
          "4. Disable auto-summary for impacted queues/tenants",
          "5. Restart transcript ingestion workers if backlog is growing",
          "6. Add/verify gating: generate summary only after transcript finalized",
          "7. Re-enable auto-summary; validate accuracy with new samples"
        ],
        "document": "data/Runbook_Copilot_SummaryAccuracy_Recovery.txt"
      },
      "tags": ["Copilot","Runbook","Summaries","Recovery"]
    },
    {
      "id": "SOP-016",
      "type": "SOP",
      "label": "P2 Communications — Copilot Summary Inaccuracy",
      "properties": {
        "sop_id": "SOP-016",
        "tenant_id": TENANT,
        "category": "Communications",
        "steps": [
          "1. Notify supervisors: summaries may be inaccurate; advise manual verification",
          "2. Disable auto-summary for impacted queues/tenants",
          "3. Post updates every 30 minutes; share mitigation status",
          "4. If impact expands: page AI Platform Reliability on-call",
          "5. After recovery: share summary + prevention (finalized-transcript gating)"
        ],
        "document": "data/SOP_Copilot_P2_Comms.txt"
      },
      "tags": ["Copilot","SOP","P2","Comms"]
    },
    {
      "id": "CFG-016",
      "type": "Configuration",
      "label": "Copilot Summarization Triggers",
      "properties": {
        "flag_id": "CFG-016",
        "tenant_id": TENANT,
        "config_area": "Copilot",
        "admin_path": "Dynamics 365 admin center > Productivity > Copilot > Summaries",
        "key_settings": [
          "Auto-summary enable/disable",
          "Trigger: transcript finalized flag required",
          "Ingestion latency thresholds",
          "Queue/tenant allowlist"
        ]
      },
      "tags": ["Copilot","Config","Summaries"]
    },
    {
      "id": "FAQ-016",
      "type": "FAQ",
      "label": "Why does Copilot add follow-ups that weren’t discussed?",
      "properties": {
        "faq_id": "FAQ-016",
        "tenant_id": TENANT,
        "question": "Why does Copilot sometimes add follow-ups or actions that weren’t discussed?",
        "answer": "This can occur when the transcript context is incomplete due to ingestion latency/backlog and summarization triggers too early. Disable auto-summary temporarily and ensure summaries run only after transcript finalization."
      },
      "tags": ["Copilot","FAQ","Summaries"]
    },
    {
      "id": "INFRA-016",
      "type": "Infrastructure",
      "label": "Copilot Inference + Transcript Workers",
      "properties": {
        "deployment_id": "INFRA-016",
        "tenant_id": TENANT,
        "resource_type": "Azure",
        "regions": ["US East","EU West"],
        "description": "Inference workers for Copilot summaries plus transcript ingestion/streaming workers.",
        "monitoring": "Application Insights + Azure Monitor"
      },
      "tags": ["Copilot","Infra","Workers"]
    },
    {
      "id": "INC-016",
      "type": "Incident",
      "label": "INC-20260302: Copilot summary hallucinations after ingestion backlog",
      "properties": {
        "incident_id": "INC-016",
        "tenant_id": TENANT,
        "date": "2026-03-02",
        "severity": "P2",
        "duration": "1 hour 05 minutes",
        "affected_service": "Copilot Conversation Intelligence",
        "affected_customers": ["RetailPlus Customer Care"],
        "root_cause": "Transcript ingestion backlog; summaries generated before transcript finalized.",
        "resolution": "Disabled auto-summary; restarted ingestion workers; added gating on finalized transcript flag.",
        "post_mortem": "Backlog alerts; enforce finalized-transcript gating; add sampling QA for summary accuracy."
      },
      "tags": ["Copilot","Incident","P2"]
    },
    {
      "id": "EXP-016",
      "type": "Expert",
      "label": "AI Platform Reliability On-Call",
      "properties": {
        "employee_id": "EXP-016",
        "role": "SRE (AI Platform Reliability)",
        "expertise": ["Copilot","LLM Reliability","Transcript Ingestion","Backpressure","Observability"],
        "email": "ai-platform-reliability-oncall@hcltech.com",
        "on_call": True,
        "location": "Bangalore, India"
      },
      "tags": ["Copilot","On-Call","Reliability"]
    },
    {
      "id": "CUST-016",
      "type": "Customer",
      "label": "RetailPlus Customer Care",
      "properties": {
        "customer_id": "CUST-016",
        "tenant_id": TENANT,
        "industry": "Retail",
        "agents_licensed": 180,
        "license_type": "Enterprise",
        "sla_tier": "Standard",
        "channels": ["Chat","Voice"],
        "region": "US West",
        "csm": "David Kim"
      },
      "tags": ["Enterprise","Retail"]
    }
  ],
  "edges": [
    # Scenario 15 links
    {"source": "SVC-015", "target": "KI-015", "type": "HAS_KNOWN_ISSUE"},
    {"source": "SVC-015", "target": "RB-015", "type": "HAS_RUNBOOK"},
    {"source": "SVC-015", "target": "SOP-015", "type": "HAS_SOP"},
    {"source": "SVC-015", "target": "CFG-015", "type": "CONFIGURED_BY"},
    {"source": "SVC-015", "target": "FAQ-015", "type": "HAS_FAQ"},
    {"source": "SVC-015", "target": "INFRA-015", "type": "RUNS_ON"},
    {"source": "KI-015", "target": "RB-015", "type": "WORKAROUND_IN"},
    {"source": "KI-015", "target": "SOP-015", "type": "WORKAROUND_IN"},
    {"source": "KI-015", "target": "CFG-015", "type": "WORKAROUND_IN"},
    {"source": "CUST-015", "target": "INC-015", "type": "REPORTED_INCIDENT"},
    {"source": "INC-015", "target": "SVC-015", "type": "IMPACTED_BY"},
    {"source": "INC-015", "target": "RB-015", "type": "RESOLVED_BY"},
    {"source": "INC-015", "target": "EXP-015", "type": "ASSIGNED_TO"},

    # Scenario 16 links
    {"source": "SVC-016", "target": "KI-016", "type": "HAS_KNOWN_ISSUE"},
    {"source": "SVC-016", "target": "RB-016", "type": "HAS_RUNBOOK"},
    {"source": "SVC-016", "target": "SOP-016", "type": "HAS_SOP"},
    {"source": "SVC-016", "target": "CFG-016", "type": "CONFIGURED_BY"},
    {"source": "SVC-016", "target": "FAQ-016", "type": "HAS_FAQ"},
    {"source": "SVC-016", "target": "INFRA-016", "type": "RUNS_ON"},
    {"source": "KI-016", "target": "RB-016", "type": "WORKAROUND_IN"},
    {"source": "KI-016", "target": "SOP-016", "type": "WORKAROUND_IN"},
    {"source": "KI-016", "target": "CFG-016", "type": "WORKAROUND_IN"},
    {"source": "CUST-016", "target": "INC-016", "type": "REPORTED_INCIDENT"},
    {"source": "INC-016", "target": "SVC-016", "type": "IMPACTED_BY"},
    {"source": "INC-016", "target": "RB-016", "type": "RESOLVED_BY"},
    {"source": "INC-016", "target": "EXP-016", "type": "ASSIGNED_TO"}
  ]
}

out_path = Path("knowledge_graph_demo_delta.json")
out_path.write_text(json.dumps(kg_delta, indent=2), encoding="utf-8")
str(out_path)

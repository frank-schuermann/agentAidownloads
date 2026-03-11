# Known Issues – Quick Reference

## 🚀 Schnellstart

### **Neue Known Issue in 2 Minuten:**

```powershell
# Interaktiver Modus (empfohlen)
python scripts/add_known_issue.py --method text --interactive

# Oder: Direkt Text-Datei erstellen
cd Knowledge_Graph_views/data
notepad KnownIssue_MyIssue.txt
# ... Template ausfüllen ...

# Generieren
cd ..
python generate_knowledge_graph.py
```

---

## 📝 Text-Dokument Template (Minimal)

```
================================================================================
KNOWN ISSUE — <Title>
================================================================================

Issue ID     : KI-2026-<NNN>
Severity     : P2
Status       : Open

SYMPTOMS:
---------
1. <Symptom>

ROOT CAUSE:
-----------
<Cause>

WORKAROUND:
-----------
1. <Step>
```

---

## 🔗 ID-Referenzen für automatische Edges

Erwähne IDs im Text für automatische Verlinkung:

```
WORKAROUND:
-----------
Follow runbook RB-VOICE-001 for recovery steps.
See FAQ-002 for additional troubleshooting.
Fixed in release NODE-2026W1.
```

**Automatisch erstellt:**
- `(KnownIssue)-[:RELATED_TO]->(Runbook)`
- `(KnownIssue)-[:RELATED_TO]->(FAQ)`
- `(KnownIssue)-[:FIXED_IN]->(ReleaseNote)`

---

## 📋 Edge Types für Known Issues

| Edge Type | Direction | Target | Beispiel |
|-----------|-----------|--------|----------|
| `RELATED_TO` | KI → | Runbook, UserGuide, SOP | Workaround documentation |
| `FIXED_IN` | KI → | ReleaseNote | Release that fixes the issue |
| `WORKAROUND_IN` | KI → | Configuration, FAQ | Configuration changes |
| `AFFECTS` | KI → | Service, Channel, Queue | Affected components |
| `HAS_KNOWN_ISSUE` | Service → | KnownIssue | Service has this issue |

---

## 🐍 Python API Examples

### Erstellen:

```python
from core.knowledge_graph import KnowledgeGraphService
from core.knowledge_graph.models.nodes import KnownIssueNode
from core.knowledge_graph.models.enums import KnownIssueSeverity, KnownIssueStatus

kg = KnowledgeGraphService(tenant_id="customer_123")

issue = KnownIssueNode(
    tenant_id="customer_123",
    issue_id="KI-2026-025",
    title="Email delays during peak hours",
    description="SMTP rate limiting causes 30-60min delays",
    severity=KnownIssueSeverity.P2,
    status=KnownIssueStatus.open,
    workaround_summary="Increase Azure quota to 1500/hour",
    workaround_steps=["Open Azure Portal", "Navigate to quotas", "Request increase"],
    affected_entities=["svc_email", "q_email_support"]
)

result = kg.add_known_issue(issue)
```

### Verlinken:

```python
# Link to Service
kg.link_service_has_known_issue("svc_email", "KI-2026-025")

# Link to Runbook (workaround)
kg.link_known_issue_workaround_in(
    issue_id="KI-2026-025",
    target_label="Runbook",
    target_id="RB-EMAIL-001"
)

# Link to Release (fix)
kg.link_known_issue_fixed_in_release(
    issue_id="KI-2026-025",
    release_id="rel_2026_w2"
)
```

### Suchen:

```python
# Keyword-basierte Suche
from core.knowledge_graph.issue_router import resolve_known_issue_from_text

result = resolve_known_issue_from_text(
    kg=kg,
    message="Emails are delayed by 30 minutes",
    limit=3
)

print(result["selected_issue_id"])  # "KI-2026-025"
print(result["selected_context"])   # Full issue details
```

### Abrufen:

```python
# Get specific issue
issue = kg.get_known_issue("KI-2026-025")

# Search by text
issues = kg.search_known_issues("email delay", limit=10)

# Get all issues for a service
cypher = """
MATCH (svc:Service {service_id: $svc_id})-[:HAS_KNOWN_ISSUE]->(ki:KnownIssue)
WHERE svc.tenant_id = $tenant_id AND ki.tenant_id = $tenant_id
RETURN ki
"""
results = kg.db.execute_read(cypher, {
    "tenant_id": kg.tenant_id,
    "svc_id": "svc_email"
})
```

---

## 🏷️ Standard Tags

| Category | Tags |
|----------|------|
| **Severity** | P0, P1, P2, P3, P4 |
| **Channels** | Voice, Chat, Email, SMS, Social |
| **Services** | Azure, ACS, Dataverse, Copilot, Routing, WFM, QM |
| **Components** | Widget, API, Queue, Agent, Analytics |
| **Status** | Open, Mitigated, Fixed, Monitoring |

---

## 🔍 Debugging

### Check if issue exists:

```powershell
# In JSON Graph
cat knowledge_graph_generated.json | Select-String "KI-2026-025"

# In Neo4j
cypher-shell -u neo4j -p password
> MATCH (ki:KnownIssue {issue_id: "KI-2026-025"}) RETURN ki;
```

### Verify edges:

```python
# Python
kg = KnowledgeGraphService(tenant_id="demo")
cypher = """
MATCH (ki:KnownIssue {issue_id: $issue_id})-[r]-(n)
WHERE ki.tenant_id = $tenant_id
RETURN type(r) as rel_type, labels(n) as target_labels, n.name as target_name
"""
edges = kg.db.execute_read(cypher, {
    "tenant_id": "demo",
    "issue_id": "KI-2026-025"
})
for e in edges:
    print(f"{e['rel_type']} -> {e['target_labels']} ({e['target_name']})")
```

---

## 📊 Status Workflow

```
Open → Mitigated → Fixed → Monitoring
  ↓         ↓          ↓         ↓
  Workaround   Patch    Release   Verify
  documented   applied  deployed  stable
```

**Status Definitions:**
- **Open**: Issue confirmed, no workaround yet
- **Mitigated**: Workaround available, not fully fixed
- **Fixed**: Permanent fix deployed
- **Monitoring**: Post-fix monitoring for recurrence

---

## 🔄 Workflow-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Issue gemeldet (Ticket/Support)                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Prüfen: Ist es ein Known Issue?                       │
│    → Suche in knowledge_graph_generated.json              │
│    → Oder: resolve_known_issue_from_text() API            │
└────────────────┬────────────────────────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
    ✅ MATCH        ❌ KEIN MATCH
         │               │
         │               ▼
         │      Neues Known Issue erstellen:
         │      1. Text-Dokument (.txt)
         │      2. Static JSON (schnell)
         │      3. Neo4j API (dynamisch)
         │               │
         │               ▼
         │      Edges hinzufügen:
         │      - WORKAROUND_IN → Runbook/FAQ
         │      - AFFECTS → Service/Queue
         │      - FIXED_IN → ReleaseNote
         │               │
         └───────┬───────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Workaround anwenden                                    │
│    → Zeige workaround_summary                             │
│    → Link zu Runbook                                      │
│    → Schritt-für-Schritt Anleitung                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 4. Ticket lösen mit Referenz zu KI-ID                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│ 5. Status aktualisieren:                                  │
│    Open → Mitigated → Fixed → Monitoring                 │
└────────────────────────────────────────────────────────────┘
```

---

## 📖 Vollständige Dokumentation

Siehe [KNOWN_ISSUES_GUIDE.md](KNOWN_ISSUES_GUIDE.md) für:
- Detaillierte Templates
- Best Practices
- Alle 3 Methoden im Detail
- API-Integration Beispiele
- Troubleshooting Guide

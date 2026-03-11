# Known Issues – Erweiterungs-Guide

## 📋 Übersicht

Dieses Dokument beschreibt **3 Wege**, um neue Known Issues zum Knowledge Graph System hinzuzufügen:

1. **Text-Dokumente** (Knowledge_Graph_views/data/*.txt) → JSON Graph
2. **Static Nodes** (Knowledge_Graph_views/static_nodes.json) → JSON Graph  
3. **Neo4j API** (core/knowledge_graph) → Graph Database

---

## **1️⃣ Methode 1: Text-Dokument erstellen**

### Schritt 1: Neues Text-Dokument anlegen

Erstelle eine neue Datei in `Knowledge_Graph_views/data/`:

```
KnownIssue_<Beschreibung>.txt
```

**Beispiel:** `KnownIssue_ChatWidgetNotLoading.txt`

### Schritt 2: Strukturiertes Format

```
================================================================================
KNOWN ISSUE — <Titel>
================================================================================

Issue ID     : KI-2026-<NNN>
Severity     : P1 | P2 | P3 | P4
Status       : Open | Workaround Available | Fix in Progress | Resolved
ETA Fix      : <Datum> (optional)
Reported     : <Datum>

AFFECTED:
---------
- Service: <Service Name>
- Versions: <Version(en)>
- Channels: <Channels> (optional)

SYMPTOMS:
---------
1. <Symptom 1>
2. <Symptom 2>
3. <Symptom 3>

ROOT CAUSE:
-----------
<Technische Beschreibung der Ursache>

IMPACT:
-------
<Business Impact / Betroffene Nutzer>

WORKAROUND:
-----------
Option 1 (Recommended): <Lösung>
  1. Schritt 1
  2. Schritt 2
  3. Schritt 3

Option 2 (Alternative): <Alternative>
  1. Schritt 1
  2. Schritt 2

MONITORING:
-----------
<Wie kann man das Problem überwachen?>

RESOLUTION TIMELINE:
--------------------
- <Datum>: <Milestone>
- <Datum>: <Milestone>
```

### Schritt 3: Generiere den Graph

```powershell
cd Knowledge_Graph_views
python generate_knowledge_graph.py
```

**Output:**
```
✓ [KnownIssue] KI-2026-005
📊 Nodes: 37
🔗 Edges: 28
```

### Schritt 4: Verlinke mit anderen Nodes (Optional)

Um Beziehungen zu erstellen, füge **ID-Referenzen** im Text ein:

**Beispiel in KnownIssue_ChatWidgetNotLoading.txt:**
```
WORKAROUND:
-----------
Option 1 (Recommended): Follow RB-CHAT-001 recovery runbook
Option 2: Apply configuration from CFG-001

RELATED FAQ:
------------
See FAQ-002 for chat widget configuration steps.
```

**Automatische Edge-Erstellung:**
- `RB-CHAT-001` im Text → Edge (KnownIssue)-[:RELATED_TO]->(Runbook)
- `FAQ-002` im Text → Edge (KnownIssue)-[:RELATED_TO]->(FAQ)

---

## **2️⃣ Methode 2: Static Nodes JSON**

Für Known Issues **ohne Dokument** (z.B. temporäre Issues):

### Schritt 1: Bearbeite `static_nodes.json`

```json
{
  "id": "KI-2026-010",
  "type": "KnownIssue",
  "label": "Email Delivery Delay > 30 minutes",
  "properties": {
    "issue_id": "KI-2026-010",
    "severity": "P2",
    "status": "Workaround Available",
    "reported": "March 10, 2026",
    "affected": "Email Channel, Queue: EMAIL-SUPPORT",
    "symptoms": "Customer emails delayed by 30-60 minutes during peak load (9 AM - 11 AM PST). Affects ~15% of email volume.",
    "root_cause": "SMTP rate limiting on Azure Communication Services. Quota set to 500/hour, but peak load reaches 800/hour.",
    "workaround": "Request Azure quota increase to 1500/hour. Monitor via Application Insights.",
    "impact": "Medium - delayed responses affect customer satisfaction but no data loss."
  },
  "tags": ["Email", "Azure", "P2", "Performance"]
}
```

### Schritt 2: Verlinke mit Edges in `static_edges.json`

```json
{
  "source": "KI-2026-010",
  "target": "CFG-EMAIL-001",
  "type": "WORKAROUND_IN",
  "description": "Email quota increase workaround documented in config"
},
{
  "source": "KI-2026-010",
  "target": "NODE-2026W1",
  "type": "FIXED_IN",
  "description": "Fixed in 2026 Wave 1 release"
},
{
  "source": "FAQ-EMAIL-001",
  "target": "KI-2026-010",
  "type": "RELATED_TO",
  "description": "Email delay FAQ references this known issue"
}
```

### Schritt 3: Regeneriere

```powershell
python generate_knowledge_graph.py
```

---

## **3️⃣ Methode 3: Neo4j API (Production)**

Für **dynamische** Known Issues zur Laufzeit:

### Schritt 1: Python API Nutzung

```python
from core.knowledge_graph import KnowledgeGraphService
from core.knowledge_graph.models.nodes import KnownIssueNode
from core.knowledge_graph.models.enums import KnownIssueSeverity, KnownIssueStatus

# Initialize service (tenant-scoped)
kg = KnowledgeGraphService(tenant_id="customer_123")

# Create Known Issue
issue = KnownIssueNode(
    tenant_id="customer_123",
    issue_id="KI-2026-015",
    title="Voice Quality Degradation on Safari Mobile",
    description="HD audio codec not supported on Safari iOS 17+, falls back to lower quality",
    severity=KnownIssueSeverity.P2,
    status=KnownIssueStatus.open,
    workaround_summary="Use Chrome or Edge mobile browser",
    workaround_steps=[
        "Notify customer to switch browser",
        "Test voice quality in Chrome/Edge",
        "Update documentation with browser recommendations"
    ],
    fixed_in_release_id="rel_2026_w3",  # Optional
    affected_entities=["ch_voice", "svc_acs", "q_support_emea"]
)

# Add to graph
result = kg.add_known_issue(issue)
print(f"Created: {result}")
```

### Schritt 2: Verlinke mit anderen Entities

```python
# Link to affected Service
kg.link_service_has_known_issue(
    service_id="svc_voice",
    issue_id="KI-2026-015"
)

# Link to Runbook (workaround)
kg.link_known_issue_workaround_in(
    issue_id="KI-2026-015",
    target_label="Runbook",
    target_id="RB-VOICE-002",
    properties={"effectiveness": "high"}
)

# Link to FAQ
kg.link_known_issue_workaround_in(
    issue_id="KI-2026-015",
    target_label="FAQ",
    target_id="FAQ-VOICE-001"
)

# Link to Release (fix)
kg.link_known_issue_fixed_in_release(
    issue_id="KI-2026-015",
    release_id="rel_2026_w3"
)

# Link to affected Channel/Queue
kg.link_known_issue_affects(
    issue_id="KI-2026-015",
    target_label="Channel",
    target_id="ch_voice"
)
```

### Schritt 3: Query & Resolve

```python
from core.knowledge_graph.issue_router import resolve_known_issue_from_text

# Find matching issue from user message
result = resolve_known_issue_from_text(
    kg=kg,
    message="Voice quality is really bad on my iPhone Safari browser",
    limit=3
)

print(result)
# Output:
# {
#   "ok": True,
#   "keywords": ["voice", "quality", "safari", "iphone"],
#   "candidates": [
#     {
#       "issue_id": "KI-2026-015",
#       "score": 0.85,
#       "service_ids": ["svc_voice", "svc_acs"],
#       "debug_hits": ["voice", "quality", "safari"]
#     }
#   ],
#   "selected_issue_id": "KI-2026-015",
#   "selected_context": { ... full issue details ... }
# }
```

---

## **🔄 Workflow-Vergleich**

| **Aspekt** | **Text-Dokument** | **Static JSON** | **Neo4j API** |
|------------|------------------|-----------------|---------------|
| **Use Case** | Dokumentierte permanente Issues | Temporäre/schnelle Issues | Dynamische Runtime Issues |
| **Versionierung** | Git-tracked | Git-tracked | Database (mit Audit Log) |
| **Editierbarkeit** | Text Editor | JSON Editor | Python Code |
| **Automatische Edges** | ✅ Via ID-Referenzen im Text | ⚠️ Manuell in static_edges.json | ✅ Via API Calls |
| **Multi-Tenant** | ❌ Single | ❌ Single | ✅ Tenant-isolated |
| **Skalierung** | Begrenzt (JSON-Größe) | Begrenzt | Unbegrenzt |
| **Suche** | Text-basiert | Text-basiert | Graph-Queries + Keyword-Matching |

---

## **📊 Best Practices**

### ✅ **DOs:**

1. **Eindeutige Issue IDs:** Verwende konsistentes Schema (z.B. `KI-<JAHR>-<NNN>`)
2. **Severity korrekt setzen:** P1 = Customer-facing Outage, P2 = Degradation, P3/P4 = Minor
3. **Status aktuell halten:** Open → Mitigated → Fixed
4. **Workarounds dokumentieren:** Schritt-für-Schritt Anleitungen
5. **Cross-Links nutzen:** Verlinke zu Runbooks, FAQs, Release Notes
6. **Tags verwenden:** Für bessere Suche und Kategorisierung

### ❌ **DON'Ts:**

1. ❌ **Keine Duplikate:** Prüfe ob Issue bereits existiert
2. ❌ **Keine sensiblen Daten:** Keine Kundennamen, interne Secrets
3. ❌ **Keine ungenauen Severity:** P0/P1 nur für echte Production Outages
4. ❌ **Keine veralteten Issues:** Archiviere gelöste Issues statt zu löschen

---

## **🔍 Issue Resolution Flow**

### Customer Support Workflow:

```
1. Ticket kommt rein: "Chat widget not loading"
   ↓
2. System sucht Known Issues via Keyword-Matching
   ↓
3. Findet KI-2025-003: Safari Chat Widget Issue
   ↓
4. Zeigt Workaround an: "Enable first-party cookie mode"
   ↓
5. Verlinkt zu Runbook: RB-CHAT-001
   ↓
6. Agent löst Ticket mit Workaround
```

### Code-Beispiel API Integration:

```python
# In Support Ticket Handler:
from core.knowledge_graph import KnowledgeGraphService
from core.knowledge_graph.issue_router import resolve_known_issue_from_text

async def handle_support_ticket(ticket_text: str, tenant_id: str):
    kg = KnowledgeGraphService(tenant_id=tenant_id)
    
    # Find matching known issue
    result = resolve_known_issue_from_text(kg, ticket_text, limit=5)
    
    if result["selected_issue_id"]:
        issue = result["selected_context"]
        
        # Return auto-response with workaround
        return {
            "message": f"This appears to be a known issue: {issue['title']}",
            "workaround": issue.get("workaround_summary"),
            "runbook": get_linked_runbook(kg, issue["issue_id"]),
            "eta_fix": issue.get("fixed_in_release_id")
        }
    
    # No match → escalate to human
    return {"message": "Escalating to live agent..."}
```

---

## **📝 Template: Neues Known Issue**

### Text-Datei Template:

```
================================================================================
KNOWN ISSUE — <Issue Title>
================================================================================

Issue ID     : KI-<YYYY>-<NNN>
Severity     : P1
Status       : Open
Reported     : <Date>

AFFECTED:
---------
- Service: <Service Name>
- Versions: <Versions>
- Regions: <Regions>

SYMPTOMS:
---------
1. <Clear symptom description>
2. <Observable behavior>
3. <Error messages if any>

ROOT CAUSE:
-----------
<Technical explanation>

IMPACT:
-------
<Business impact, affected customers, SLA impact>

WORKAROUND:
-----------
Option 1 (Recommended): <Solution>
  1. <Step>
  2. <Step>
  3. <Step>

RESOLUTION TIMELINE:
--------------------
- <Date>: Issue identified
- <Date>: Root cause confirmed
- <Date>: Fix ETA
```

### JSON Template:

```json
{
  "id": "KI-<YYYY>-<NNN>",
  "type": "KnownIssue",
  "label": "<Short Title>",
  "properties": {
    "issue_id": "KI-<YYYY>-<NNN>",
    "severity": "P1",
    "status": "Open",
    "reported": "<Date>",
    "affected": "<Affected systems>",
    "symptoms": "<Symptom description>",
    "root_cause": "<Root cause>",
    "workaround": "<Workaround steps>",
    "impact": "<Impact description>"
  },
  "tags": ["<Tag1>", "<Tag2>", "<Tag3>"]
}
```

---

## **🚀 Quick Start**

### Neues Known Issue in 5 Minuten:

```powershell
# 1. Erstelle Text-Datei
cd Knowledge_Graph_views/data
notepad KnownIssue_MyNewIssue.txt

# 2. Fülle Template aus (siehe oben)

# 3. Generiere Graph
cd ..
python generate_knowledge_graph.py

# 4. Verifikation
echo "Prüfe knowledge_graph_generated.json..."
# Suche nach deiner neuen Issue ID

# 5. Optional: Füge Edges in static_edges.json hinzu

# 6. Regeneriere
python generate_knowledge_graph.py

# 7. Commit & Push
git add .
git commit -m "feat: Add KI-<ID> - <Title>"
git push
```

**Fertig! 🎉**

---

## **📚 Weiterführende Ressourcen**

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System-Architektur
- [core/knowledge_graph/models/nodes.py](../core/knowledge_graph/models/nodes.py) - Node-Definitionen
- [core/knowledge_graph/service_ccas.py](../core/knowledge_graph/service_ccas.py) - CCaaS Service API
- [core/knowledge_graph/issue_router.py](../core/knowledge_graph/issue_router.py) - Issue Resolution Logic

---

## **❓ FAQ**

**Q: Kann ich Known Issues nachträglich bearbeiten?**
A: Ja! Bei Text-Dateien: Einfach .txt bearbeiten und regenerieren. Bei Neo4j: `kg.create_node()` macht ein MERGE (Update).

**Q: Wie archiviere ich gelöste Issues?**
A: Setze `status: "Fixed"` und optional `fixed_in_release_id`. Lösche NICHT die Datei (historische Referenz).

**Q: Wie verlinke ich mehrere Runbooks?**
A: Text-Methode: Erwähne alle IDs im Text. JSON: Mehrere Edges in static_edges.json. API: Mehrere `link_known_issue_workaround_in()` Calls.

**Q: Kann ich Custom Properties hinzufügen?**
A: Ja! Im Properties-Dictionary kannst du beliebige Key-Value-Paare ergänzen.

**Q: Wie funktioniert das Keyword-Matching?**
A: Siehe [issue_router.py](../core/knowledge_graph/issue_router.py) - Keywords werden aus Symptomen, Titel, und Affected Services extrahiert und gematched.

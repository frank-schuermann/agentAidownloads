# Bulk Document Import - Comprehensive Guide

Automatischer Import mehrerer Dokumente aus ZIP-Archiven in den Knowledge Graph mit **intelligenter Beziehungserkennung**.

---

## 📋 Überblick

Das Bulk Import System ermöglicht:

✅ **ZIP-Upload** mit gemischten Dokumenttypen (Runbooks, FAQs, SOPs, User Guides, Known Issues)  
✅ **Automatische Typ-Erkennung** aus Dateiname und Inhalt  
✅ **Automatische Node-Erstellung** in Neo4j  
✅ **Intelligente Edge-Inferenz** über 3 Mechanismen:
   - **Explizite Referenzen** (KI-001 erwähnt RB-002)
   - **Keyword-Overlap** (beide über 'voice' + 'routing')
   - **Naming-Patterns** (KI-Voice-Transfer ↔ Runbook-Voice-Outage)

---

## 🚀 Schnellstart

### **1. Dokumente vorbereiten**

Erstelle eine ZIP-Datei mit strukturierten Text-Dokumenten:

```
documents.zip
├── KnownIssue_Voice_Transfer_Drop.txt
├── Runbook_Voice_Outage_Recovery.txt
├── FAQ_Voice_Quality.txt
├── SOP_P1_Escalation.txt
├── UserGuide_Agent_Desktop.txt
└── SPO_CCaaS_Enterprise.txt
```

**Naming Convention (empfohlen):**

| Prefix | Typ | Beispiel |
|--------|-----|----------|
| `KnownIssue_` | Known Issue | `KnownIssue_Voice_Transfer_Drop.txt` |
| `Runbook_` | Runbook | `Runbook_Voice_Outage.txt` |
| `FAQ_` | FAQ | `FAQ_Presence_Reset.txt` |
| `SOP_` | Standard Operating Procedure | `SOP_P1_Escalation.txt` |
| `SPO_` | Standard Practice Operations | `SPO_CCaaS_Digital.txt` |
| `UserGuide_` | User Guide | `UserGuide_AgentDesktop.txt` |
| `Guide_` | User Guide | `Guide_Setup.txt` |

**Alternative:** Typ-Erkennung aus Inhalt (falls Naming Convention nicht genutzt)

---

### **2. Import via CLI**

```powershell
# Basic Import
python scripts/bulk_import_documents.py --zip documents.zip

# Ohne Edge-Inferenz (nur Nodes)
python scripts/bulk_import_documents.py --zip docs.zip --no-edges

# Höhere Confidence für Edges
python scripts/bulk_import_documents.py --zip docs.zip --confidence 0.7

# Anderer Tenant
python scripts/bulk_import_documents.py --zip docs.zip --tenant my_tenant
```

**Output:**
```
================================================================================
🚀 Bulk Document Import - Knowledge Graph
================================================================================
📁 ZIP File:     documents.zip
🏢 Tenant:       tenant_demo
🔗 Create Edges: Yes
📊 Min Confidence: 0.5
================================================================================

⏳ Importing documents...

✅ Processed KnownIssue_Voice_Transfer_Drop.txt → KnownIssue (KI-Voice_Transfer_Drop)
✅ Processed Runbook_Voice_Outage.txt → Runbook (RB-Voice_Outage)
✅ Processed FAQ_Voice_Quality.txt → FAQ (FAQ-Voice_Quality)

================================================================================
✅ Import Completed
================================================================================

📊 Statistics:
   Files Processed:  6
   Nodes Created:    6
   Edges Created:    8
   Errors:           0

🕐 Timestamp: 2026-03-10T14:22:31Z

📄 Full report saved: import_report_tenant_demo.json
```

---

### **3. Import via REST API**

```bash
curl -X POST "http://localhost:8000/api/bulk-import/zip" \
  -F "file=@documents.zip" \
  -F "tenant_id=tenant_demo" \
  -F "create_edges=true" \
  -F "min_edge_confidence=0.6"
```

**Response:**
```json
{
  "status": "completed",
  "stats": {
    "files_processed": 6,
    "nodes_created": 6,
    "edges_created": 8,
    "errors": []
  },
  "timestamp": "2026-03-10T14:22:31Z"
}
```

**API Documentation:**  
→ http://localhost:8000/docs#/bulk-import/import_from_zip_api_bulk_import_zip_post

---

## 🧠 Intelligente Edge-Inferenz

### **Mechanismus 1: Explicit References**

Dokumente referenzieren andere Entities explizit:

**Beispiel: Known Issue verweist auf Runbook**

```
Known Issue: KI-Voice-Transfer-Drop
Title: Voice transfer calls drop unexpectedly

Workaround:
Follow Runbook RB-Voice-Outage to restart the voice gateway.
Also check FAQ-Voice-Quality for common issues.
```

**Erkannte Edges:**
- `KI-Voice-Transfer-Drop` -[WORKAROUND_IN]→ `RB-Voice-Outage`
- `KI-Voice-Transfer-Drop` -[DOCUMENTED_IN]→ `FAQ-Voice-Quality`

---

### **Mechanismus 2: Keyword-Based Semantic Matching**

Dokumente mit gemeinsamen Keywords werden verlinkt:

**Beispiel:**

**KI-Voice-Transfer-Drop.txt:**
```
...voice, routing, call transfer, queue overflow...
```

**Runbook-Voice-Outage.txt:**
```
...voice channel outage, routing rules, queue timeout...
```

**Gemeinsame Keywords:** `voice`, `routing`, `queue` → **RELATED_TO** Edge

**Threshold:** Mindestens 2 gemeinsame Keywords (konfigurierbar)

---

### **Mechanismus 3: Naming Pattern Matching**

Ähnliche Namen deuten auf Beziehung hin:

**Beispiel:**
- `KI-Voice-Transfer-Drop` ↔ `RB-Voice-Outage`
- `FAQ-Copilot-Slow` ↔ `KI-Copilot-Latency`

**Similarity Score:** Token-based Jaccard Similarity  
`similarity = len(tokens1 ∩ tokens2) / len(tokens1 ∪ tokens2)`

**Threshold:** 0.5 (konfigurierbar via `min_edge_confidence`)

---

## 📐 Edge-Typen

Je nach Dokumenttyp-Kombination werden passende Edge-Typen erstellt:

| Von | Zu | Edge-Typ | Bedeutung |
|-----|----|----------|-----------|
| Known Issue | Runbook | `WORKAROUND_IN` | Runbook ist Workaround |
| Known Issue | Runbook | `RESOLVED_BY` | Runbook löst Issue |
| Known Issue | FAQ | `DOCUMENTED_IN` | FAQ dokumentiert Issue |
| SOP | Runbook | `HAS_RUNBOOK` | SOP nutzt Runbook |
| UserGuide | FAQ | `HAS_FAQ` | Guide verweist auf FAQ |
| * | * | `RELATED_TO` | Generische Beziehung |

---

## 📝 Dokumentformat-Templates

### **Known Issue Template**

```
KNOWN ISSUE — KI-Voice-Transfer-Drop
Voice transfer calls drop unexpectedly

--- DESCRIPTION ---
ID: KI-Voice-Transfer-Drop
Title: Voice transfer calls drop unexpectedly
Category: Voice
Priority: P2

--- SYMPTOMS ---
- Call drops when agent transfers
- Customer hears silence then disconnect
- Affects ~5% of transfers

--- ROOT CAUSE ---
Race condition in SIP session handoff during transfer

--- WORKAROUND ---
Follow Runbook RB-Voice-Outage to restart voice gateway.
Temporarily disable warm transfers and use cold transfers.

--- AFFECTED SERVICES ---
- Voice Channel
- Transfer Service
- SIP Gateway

--- REFERENCES ---
- Runbook: RB-Voice-Outage
- FAQ: FAQ-Voice-Quality
- SOP: SOP-P2-Incident
```

**Automatisch erkannt:**
- Type: `KnownIssue`
- Node Label: `KnownIssue`
- ID: `KI-Voice-Transfer-Drop`
- Edges: → `RB-Voice-Outage`, `FAQ-Voice-Quality`, `SOP-P2-Incident`

---

### **Runbook Template**

```
RUNBOOK — RB-Voice-Outage
Voice Channel Outage Recovery

--- DESCRIPTION ---
Diagnose and recover from voice channel outages

--- STEPS ---
1. Check Azure Communication Services status
2. Verify SIP trunk connectivity
3. Restart voice gateway pods
4. Validate call flow with test call
5. Monitor for 15 minutes

--- SUCCESS RATE ---
82% (41 successful executions)

--- AUTHOR ---
SRE Team

--- RELATED ---
- Known Issues: KI-Voice-Transfer-Drop, KI-Voice-Quality
- SOP: SOP-P1-Escalation
```

---

### **FAQ Template**

```
FAQ — FAQ-Voice-Quality
Voice quality issues and troubleshooting

--- QUESTION ---
Why is the voice quality poor during calls?

--- ANSWER ---
Poor voice quality can be caused by:
1. Network latency (check ping to Azure regions)
2. Insufficient bandwidth (min 100 kbps per call)
3. Codec mismatch (ensure G.711 is enabled)
4. Packet loss (check QoS settings)

Follow Runbook RB-Voice-Diagnostics for detailed troubleshooting.

--- CATEGORY ---
Voice

--- RELATED ---
- Runbook: RB-Voice-Diagnostics
- Known Issue: KI-Voice-Transfer-Drop
```

---

### **SOP Template**

```
SOP — SOP-P1-Escalation
P1 Incident Escalation Procedure

--- DESCRIPTION ---
Standard Operating Procedure for P1 incident escalation

--- CATEGORY ---
incident_response

--- APPROVAL REQUIRED ---
Yes - VP Engineering for customer-facing outages

--- STEPS ---
1. Declare P1 incident in Slack (#incidents)
2. Page on-call engineer via PagerDuty
3. Create war room (Teams/Zoom)
4. Update status page every 15 minutes
5. Engage vendor support if needed (see Runbook RB-Vendor-Escalation)
6. Post-incident review within 48 hours

--- RELATED ---
- Runbook: RB-Vendor-Escalation
- SOP: SOP-PostIncidentReview
```

---

### **User Guide Template**

```
USER GUIDE — UserGuide-AgentDesktop
Agent Desktop Setup and Configuration

--- DESCRIPTION ---
How to set up and configure the CCaaS Agent Desktop

--- SECTIONS ---

## Installation
1. Download installer from portal
2. Run installer with admin privileges
3. Enter organization ID

## Configuration
- Set presence to Available
- Configure softphone settings
- Enable screen pop

## Troubleshooting
For common issues, see FAQ-AgentDesktop-Issues
For escalation, follow SOP-P2-Support

--- RELATED ---
- FAQ: FAQ-AgentDesktop-Issues
- SOP: SOP-P2-Support
```

---

## 🎯 Use Cases

### **Use Case 1: Neues Feature mit kompletter Dokumentation**

**Szenario:** Ein neues "Copilot für Agents"-Feature wird released.

**Dokumente:**
- `UserGuide_Copilot_Setup.txt` - Setup-Anleitung
- `FAQ_Copilot_Common.txt` - Häufige Fragen
- `KnownIssue_Copilot_Latency.txt` - Bekanntes Latenz-Problem
- `Runbook_Copilot_Reset.txt` - Troubleshooting
- `SOP_Copilot_Enablement.txt` - Rollout-Prozess

**ZIP erstellen:**
```powershell
Compress-Archive -Path copilot_docs\* -DestinationPath copilot_feature.zip
```

**Import:**
```powershell
python scripts/bulk_import_documents.py --zip copilot_feature.zip --confidence 0.6
```

**Ergebnis:**
- 5 Nodes erstellt
- 8-12 Edges inferiert (basierend auf Referenzen und Keywords)
- Vollständig verknüpftes Feature-Subgraph

---

### **Use Case 2: Migration alter Confluence-Dokumentation**

**Szenario:** 50+ Confluence-Seiten sollen in Knowledge Graph migriert werden.

**Vorbereitung:**
1. Confluence-Seiten als Markdown exportieren
2. Dateien umbenennen nach Naming Convention
3. ZIP-Archiv erstellen

**Import:**
```powershell
python scripts/bulk_import_documents.py --zip confluence_export.zip --no-edges
```

**Nachbearbeitung:**
```cypher
// Manuelle Edges für spezielle Beziehungen
MATCH (doc:Document {doc_id: 'doc-architecture'})
MATCH (svc:Service {service_id: 'svc_voice'})
MERGE (doc)-[:DOCUMENTS]->(svc)
```

---

### **Use Case 3: Incident Post-Mortem Knowledge Capture**

**Szenario:** Nach P0-Incident soll das gewonnene Wissen persistent gespeichert werden.

**Dokumente:**
- `KnownIssue_DB_Failover_2026_03.txt`
- `Runbook_DB_Failover_Recovery.txt`
- `SOP_PostIncidentReview_Updated.txt`

**ZIP & Import:**
```powershell
Compress-Archive -Path incident_docs\* -DestinationPath incident_2026_03.zip
python scripts/bulk_import_documents.py --zip incident_2026_03.zip
```

**Graph Query:**
```cypher
MATCH (ki:KnownIssue {issue_id: 'ki-db_failover_2026_03'})
MATCH (ki)-[r:RESOLVED_BY]->(rb:Runbook)
RETURN ki, r, rb
```

---

## 🔧 Konfiguration

### **Edge Confidence Threshold**

```python
# Niedriger Threshold (mehr Edges, evtl. False Positives)
min_edge_confidence = 0.3

# Standard (balanced)
min_edge_confidence = 0.5

# Hoher Threshold (weniger Edges, nur High Confidence)
min_edge_confidence = 0.7
```

### **Keyword-Kategorien erweitern**

Editiere `core/knowledge_graph/bulk_import_service.py`:

```python
class KeywordExtractor:
    CATEGORIES = {
        "voice": [...],
        "chat": [...],
        # Neue Kategorie
        "billing": ["invoice", "pricing", "subscription", "payment"],
    }
```

### **Edge-Typ-Regeln anpassen**

```python
class EdgeInferenceEngine:
    def _get_edge_type_for_pair(self, type1: str, type2: str):
        pairs = {
            ("KnownIssue", "Runbook"): "RESOLVED_BY",
            # Neue Regel
            ("SOP", "Document"): "REFERENCES",
        }
```

---

## 📊 Monitoring & Debugging

### **Import-Report analysieren**

Nach jedem Import wird ein Report gespeichert:

```json
{
  "status": "completed",
  "stats": {
    "files_processed": 6,
    "nodes_created": 6,
    "edges_created": 8,
    "errors": [
      {
        "filename": "broken_file.txt",
        "error": "Invalid UTF-8 encoding"
      }
    ]
  },
  "timestamp": "2026-03-10T14:22:31Z"
}
```

### **Neo4j Queries**

**Alle importierten Nodes anzeigen:**
```cypher
MATCH (n {tenant_id: 'tenant_demo'})
WHERE n.created_at > datetime() - duration({hours: 1})
RETURN n
```

**Edges mit niedriger Confidence finden:**
```cypher
MATCH (a)-[r]->(b)
WHERE r.confidence < 0.6
RETURN a, r, b
ORDER BY r.confidence ASC
```

**Nodes ohne Edges (Orphans):**
```cypher
MATCH (n {tenant_id: 'tenant_demo'})
WHERE NOT (n)--()
RETURN n
```

---

## ⚠️ Best Practices

### ✅ **DO:**
- Nutze Naming Convention für präzise Typ-Erkennung
- Verwende strukturierte Templates
- Referenziere andere Dokumente explizit (KI-001, RB-002)
- Teste mit kleinem ZIP zuerst
- Überprüfe Import-Report auf Errors

### ❌ **DON'T:**
- Keine Binär-Dateien (PDFs, DOCX) im ZIP
- Keine riesigen Dateien (>1 MB pro Dokument)
- Keine doppelten IDs (wird überschrieben)
- Keine Sonderzeichen in Dateinamen

---

## 🐛 Troubleshooting

### **Problem: Keine Edges erstellt**

**Ursache:** Zu hoher `min_edge_confidence` Threshold

**Lösung:**
```powershell
python scripts/bulk_import_documents.py --zip docs.zip --confidence 0.3
```

---

### **Problem: Falsche Node-Typen erkannt**

**Ursache:** Dateiname folgt nicht Naming Convention

**Lösung:** Dateien umbenennen oder Content-Keywords verstärken

**Beispiel:**
```
# Vorher
guide_for_setup.txt  → Erkannt als Document

# Nachher
UserGuide_Setup.txt → Erkannt als UserGuide
```

---

### **Problem: UTF-8 Encoding Errors**

**Ursache:** Dateien mit falschem Encoding

**Lösung:**
```powershell
# PowerShell: Dateien zu UTF-8 konvertieren
Get-ChildItem *.txt | ForEach-Object {
    $content = Get-Content $_.FullName
    Set-Content -Path $_.FullName -Value $content -Encoding UTF8
}
```

---

### **Problem: Neo4j Connection Failed**

**Ursache:** Neo4j nicht gestartet

**Lösung:**
```powershell
docker-compose up -d neo4j
```

---

## 📖 API Reference

### **POST /api/bulk-import/zip**

**Request:**
```bash
curl -X POST "http://localhost:8000/api/bulk-import/zip" \
  -F "file=@documents.zip" \
  -F "tenant_id=tenant_demo" \
  -F "create_edges=true" \
  -F "min_edge_confidence=0.5"
```

**Parameters:**
- `file`: ZIP archive (multipart/form-data)
- `tenant_id`: Tenant ID (default: `tenant_demo`)
- `create_edges`: Infer edges (default: `true`)
- `min_edge_confidence`: Min confidence (default: `0.5`, range: `0.0-1.0`)

**Response:**
```json
{
  "status": "completed",
  "stats": {
    "files_processed": 6,
    "nodes_created": 6,
    "edges_created": 8,
    "errors": []
  },
  "timestamp": "2026-03-10T14:22:31Z"
}
```

---

### **GET /api/bulk-import/status**

**Request:**
```bash
curl http://localhost:8000/api/bulk-import/status
```

**Response:**
```json
{
  "status": "online",
  "service": "Bulk Document Import",
  "supported_formats": [".txt", ".md", ".markdown"],
  "supported_types": [
    "Runbook", "KnownIssue", "FAQ", "SOP", "SPO",
    "UserGuide", "Configuration", "Infrastructure", "Document"
  ],
  "edge_inference": [
    "Explicit references",
    "Keyword-based semantic",
    "Naming pattern matching"
  ]
}
```

---

## 🔗 Verwandte Dokumentation

- [KNOWN_ISSUES_GUIDE.md](KNOWN_ISSUES_GUIDE.md) - Known Issues Management
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System-Architektur
- [LOCAL_DEV_KNOWLEDGE_GRAPH.md](LOCAL_DEV_KNOWLEDGE_GRAPH.md) - Neo4j Setup

---

## 🤝 Support

Bei Fragen oder Problemen:
- GitHub Issues: [Link]
- Slack Channel: #knowledge-graph
- Email: kg-support@company.com

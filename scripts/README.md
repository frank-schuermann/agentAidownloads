# Scripts – Knowledge Graph Tools

Dieses Verzeichnis enthält Utility-Scripts für Knowledge Graph Management.

---

## 📋 Verfügbare Scripts

### **1. `add_known_issue.py` – Known Issue Creator**

Erstellt neue Known Issues über 3 verschiedene Methoden.

#### **Usage:**

```powershell
# Interaktiver Modus (empfohlen)
python scripts/add_known_issue.py --method text --interactive
python scripts/add_known_issue.py --method json --interactive
python scripts/add_known_issue.py --method neo4j --interactive

# Nur Hilfe anzeigen
python scripts/add_known_issue.py --help
```

---

### **2. `bulk_import_documents.py` – Bulk Document Import (NEU!)**

Importiert mehrere Dokumente aus ZIP-Archiv in den Knowledge Graph mit **intelligenter Beziehungserkennung**.

#### **Features:**
- ✅ ZIP-Upload mit gemischten Dokumenttypen
- ✅ Automatische Typ-Erkennung (Runbook, FAQ, SOP, UserGuide, Known Issue, SPO)
- ✅ Intelligente Edge-Inferenz (Explicit References + Keyword Matching + Naming Patterns)
- ✅ Neo4j-Integration

#### **Usage:**

```powershell
# Standard Import
python scripts/bulk_import_documents.py --zip documents.zip

# Ohne Edge-Inferenz (nur Nodes)
python scripts/bulk_import_documents.py --zip docs.zip --no-edges

# Höhere Confidence für Edges
python scripts/bulk_import_documents.py --zip docs.zip --confidence 0.7

# Anderer Tenant
python scripts/bulk_import_documents.py --zip docs.zip --tenant my_tenant

# Verbose Output
python scripts/bulk_import_documents.py --zip docs.zip --verbose
```

#### **Beispiel-Workflow:**

```powershell
# 1. Beispiel-Dokumente testen
cd C:\projects\kg\kg\examples\bulk_import_samples
Compress-Archive -Path *.txt -DestinationPath sample_docs.zip

# 2. Import
cd C:\projects\kg\kg
python scripts/bulk_import_documents.py --zip examples\bulk_import_samples\sample_docs.zip

# 3. Ergebnis prüfen
# → Output zeigt: Nodes Created, Edges Created
# → import_report_tenant_demo.json
```

#### **Unterstützte Dokumenttypen:**
- `KnownIssue_*.txt` → KnownIssue Node (KI-*)
- `Runbook_*.txt` → Runbook Node (RB-*)
- `FAQ_*.txt` → FAQ Node (FAQ-*)
- `SOP_*.txt` → SOP Node (SOP-*)
- `SPO_*.txt` → Document Node (SPO-*)
- `UserGuide_*.txt` → Document Node (UG-*)

#### **Dokumentation:**
- [BULK_IMPORT_GUIDE.md](../docs/BULK_IMPORT_GUIDE.md) - Umfassender Guide
- [BULK_IMPORT_QUICK_REFERENCE.md](../docs/BULK_IMPORT_QUICK_REFERENCE.md) - Quick Reference
- [examples/bulk_import_samples/](../examples/bulk_import_samples/) - Beispiel-Dokumente

---

### **3. `convert_cases_to_uta_knowledge.py`**

#### **Methoden:**

- **text**: Erstellt strukturierte .txt-Datei in `Knowledge_Graph_views/data/`
- **json**: Fügt Node zu `static_nodes.json` hinzu
- **neo4j**: Erstellt direkt in Neo4j Graph Database (erfordert laufende Neo4j-Instanz)

#### **Beispiel-Workflow (Text-Methode):**

```powershell
PS C:\projects\kg\kg> python scripts/add_known_issue.py --method text --interactive

================================================================================
🚀 Known Issue Creator - Method: TEXT
================================================================================

Issue ID (e.g., KI-2026-020): KI-2026-030
Title: Email notifications delayed
Severity (P0/P1/P2/P3/P4) [P2]: P2
Status (Open/Mitigated/Fixed) [Open]: Open

Symptoms (one per line, empty line to finish):
  - Notification emails delayed by 30-60 minutes
  - Affects all email notifications
  - 

Root Cause: SMTP rate limiting on Azure Communication Services

Impact: Delayed customer notifications, affects customer satisfaction

Workaround steps (one per line, empty line to finish):
  - Request Azure quota increase to 1500/hour
  - Monitor via Application Insights
  - 

Tags (comma-separated): Email, Azure, P2, Performance

✅ Created text document: Knowledge_Graph_views/data/KnownIssue_KI_2026_030.txt
📝 Next steps:
   1. Edit the file to complete missing sections
   2. Run: python generate_knowledge_graph.py
   3. Verify in knowledge_graph_generated.json
```

---

## 🧪 Neo4j Seed Scripts

Diese Scripts befüllen die Neo4j-Datenbank mit Testdaten.

### **`kg_seed_*.py` – Data Seeding**

```powershell
# Minimale Demo-Daten (schnell)
python scripts/kg_seed_minimal.py

# Spezifische Bereiche seeden
python scripts/kg_seed_business_minimal.py       # Organizational structure
python scripts/kg_seed_ccas_poc.py               # CCaaS POC data
python scripts/kg_seed_docs_minimal.py           # Documentation
python scripts/kg_seed_incidents_minimal.py      # Sample incidents
python scripts/kg_seed_runbooks_minimal.py       # Runbooks
python scripts/kg_seed_sop_minimal.py            # SOPs
```

### **`kg_test_*.py` – Testing**

```powershell
# Test Known Issues routing
python scripts/test_kg_agent.py

# Smoke tests für Incidents
python scripts/kg_smoke_tests_incidents.py

# Query-Tests
python scripts/kg_test_business_queries.py
python scripts/kg_smoke_test_queries.py
```

---

## 🚀 Deployment & Development

### **`run_dev.sh` / `setup.sh`**
Development environment setup (Bash)

### **`deploy-frontend.sh` / `deploy-frontend.ps1`**
Frontend deployment scripts

### **`docker-entrypoint.sh`**
Docker container entrypoint

---

## 🛠️ Weitere geplante Scripts

### **`import_runbooks.py`** (geplant)
Bulk-Import von Runbooks aus Markdown/Confluence

### **`export_to_neo4j.py`** (geplant)
Exportiert JSON Graph → Neo4j Database

### **`validate_graph.py`** (geplant)
Validiert JSON Graph auf:
- Duplizierte IDs
- Broken edges (referenzierte Nodes fehlen)
- Schema-Konformität
- Best Practice Violations

### **`generate_report.py`** (geplant)
Erstellt Berichte über:
- Known Issues nach Severity
- Services mit meisten Issues
- Offene vs. Fixed Issues Timeline
- Missing Workarounds

---

## 💡 Eigene Scripts erstellen

Beispiel-Template für neue Scripts:

```python
#!/usr/bin/env python3
"""
Script Name - Description

Usage:
    python scripts/my_script.py --help
"""

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="My Script")
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    
    args = parser.parse_args()
    
    print(f"Processing {args.input} → {args.output}")
    # ... your logic here ...

if __name__ == '__main__':
    main()
```

---

## 📖 Dokumentation

- [KNOWN_ISSUES_GUIDE.md](../docs/KNOWN_ISSUES_GUIDE.md) - Umfassender Guide
- [KNOWN_ISSUES_QUICK_REFERENCE.md](../docs/KNOWN_ISSUES_QUICK_REFERENCE.md) - Quick Reference
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System-Architektur

---

## 🤝 Beitragen

Neue Scripts hinzufügen:

1. **Erstelle Script** in `scripts/`
2. **Dokumentiere** in diesem README
3. **Füge Hilfe-Text** hinzu (`--help`)
4. **Teste** mit verschiedenen Inputs
5. **Commit & Push**

**Naming Convention:**
- `verb_noun.py` (z.B. `add_known_issue.py`, `export_to_neo4j.py`)
- Verwende Unterstriche (nicht Bindestriche)
- Kurz und beschreibend

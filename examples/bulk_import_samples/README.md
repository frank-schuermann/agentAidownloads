# Bulk Import Sample Documents

This directory contains example documents for testing the Bulk Document Import service.

## 📁 Contents

| File | Type | ID | Description |
|------|------|----|-------------|
| `KnownIssue_Voice_Transfer_Drop.txt` | Known Issue | KI-Voice-Transfer-Drop | Voice transfers dropping during handoff |
| `Runbook_Voice_Outage.txt` | Runbook | RB-Voice-Outage | Voice channel recovery procedures |
| `FAQ_Voice_Quality.txt` | FAQ | FAQ-Voice-Quality | Troubleshooting voice quality issues |
| `SOP_P2_Incident.txt` | SOP | SOP-P2-Incident | P2 incident response procedure |
| `UserGuide_AgentDesktop.txt` | User Guide | UserGuide-AgentDesktop | Agent Desktop setup and usage |
| `SPO_CCaaS_Enterprise.txt` | SPO | SPO-CCaaS-Enterprise | Enterprise platform operations |

## 🔗 Expected Relationships

When imported, these documents will create the following edges:

### Explicit References (from content)
- `KI-Voice-Transfer-Drop` -[WORKAROUND_IN]→ `RB-Voice-Outage`
- `KI-Voice-Transfer-Drop` -[DOCUMENTED_IN]→ `FAQ-Voice-Quality`
- `KI-Voice-Transfer-Drop` -[RELATED_TO]→ `SOP-P2-Incident`
- `RB-Voice-Outage` -[RELATED_TO]→ `SOP-P1-Escalation` (referenced in content)
- `FAQ-Voice-Quality` -[RELATED_TO]→ `RB-Voice-Diagnostics` (referenced)
- `SOP-P2-Incident` -[HAS_RUNBOOK]→ `RB-Voice-Outage`
- `UserGuide-AgentDesktop` -[RELATED_TO]→ `KI-Voice-Transfer-Drop`
- `UserGuide-AgentDesktop` -[RELATED_TO]→ `FAQ-Voice-Quality`
- `SPO-CCaaS-Enterprise` -[HAS_KNOWN_ISSUE]→ `KI-Voice-Transfer-Drop`

### Keyword-Based Semantic (from shared keywords)
- `KI-Voice-Transfer-Drop` ↔ `RB-Voice-Outage` (voice, sip, routing)
- `KI-Voice-Transfer-Drop` ↔ `FAQ-Voice-Quality` (voice, quality)
- `RB-Voice-Outage` ↔ `FAQ-Voice-Quality` (voice, diagnostics)
- `UserGuide-AgentDesktop` ↔ `KI-Voice-Transfer-Drop` (voice, transfer)

### Naming Patterns
- `KI-Voice-Transfer-Drop` ↔ `RB-Voice-Outage` (both contain "Voice")
- `FAQ-Voice-Quality` ↔ `RB-Voice-Outage` (both contain "Voice")

## 🚀 How to Test

### 1. Create ZIP Archive

```powershell
# From the examples directory
Compress-Archive -Path bulk_import_samples\*.txt -DestinationPath sample_documents.zip
```

### 2. Import via CLI

```powershell
cd C:\projects\kg\kg
python scripts/bulk_import_documents.py --zip examples\sample_documents.zip --verbose
```

### 3. Verify in Neo4j

```cypher
// Check created nodes
MATCH (n {tenant_id: 'tenant_demo'})
WHERE n.issue_id IN ['ki-voice-transfer-drop'] 
   OR n.runbook_id IN ['rb-voice-outage']
   OR n.faq_id IN ['faq-voice-quality']
RETURN n

// Check edges
MATCH (a)-[r]->(b)
WHERE a.tenant_id = 'tenant_demo' 
  AND b.tenant_id = 'tenant_demo'
  AND r.confidence IS NOT NULL
RETURN a.title, type(r), b.title, r.confidence, r.reason
ORDER BY r.confidence DESC
```

### 4. Test via API

```bash
curl -X POST "http://localhost:8000/api/bulk-import/zip" \
  -F "file=@examples/sample_documents.zip" \
  -F "tenant_id=tenant_demo" \
  -F "create_edges=true" \
  -F "min_edge_confidence=0.5"
```

## 📊 Expected Results

**Nodes Created:** 6
- 1 KnownIssue
- 1 Runbook
- 1 FAQ
- 1 SOP
- 1 Document (UserGuide)
- 1 Document (SPO)

**Edges Created:** 10-15 (depending on confidence threshold)
- 6-8 explicit reference edges (confidence = 1.0)
- 3-5 keyword-based edges (confidence = 0.4-0.8)
- 1-2 naming pattern edges (confidence = 0.5-0.7)

## 🎯 What to Verify

✅ All 6 files processed without errors  
✅ Node IDs generated correctly (KI-*, RB-*, FAQ-*, etc.)  
✅ Titles extracted from content  
✅ Edge types match expected relationships  
✅ Confidence scores reasonable (0.5-1.0)  
✅ No duplicate edges  
✅ Keywords extracted correctly  

## 🐛 Troubleshooting

If import fails:
1. Check Neo4j is running: `docker ps | grep neo4j`
2. Check file encoding is UTF-8
3. Verify ZIP contains .txt files only
4. Run with `--verbose` flag for detailed logs
5. Check `import_report_tenant_demo.json` for error details

## 📖 Related Documentation

- [BULK_IMPORT_GUIDE.md](../../docs/BULK_IMPORT_GUIDE.md) - Full guide
- [BULK_IMPORT_QUICK_REFERENCE.md](../../docs/BULK_IMPORT_QUICK_REFERENCE.md) - Quick ref

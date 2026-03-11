# Bulk Import - Quick Reference

## 🚀 Schnellstart

```powershell
# 1. ZIP mit Dokumenten erstellen
Compress-Archive -Path docs\* -DestinationPath documents.zip

# 2. Import
python scripts/bulk_import_documents.py --zip documents.zip

# 3. Ergebnis prüfen
# → import_report_tenant_demo.json
```

---

## 📁 Naming Convention

| Prefix | Typ | ID-Format |
|--------|-----|-----------|
| `KnownIssue_` | Known Issue | `KI-{Name}` |
| `Runbook_` | Runbook | `RB-{Name}` |
| `FAQ_` | FAQ | `FAQ-{Name}` |
| `SOP_` | SOP | `SOP-{Name}` |
| `SPO_` | SPO | `SPO-{Name}` |
| `UserGuide_` | User Guide | `UG-{Name}` |

**Beispiel:** `KnownIssue_Voice_Drop.txt` → `KI-Voice_Drop`

---

## 🧠 Edge-Inferenz

### Explicit References
```
Workaround: Follow Runbook RB-Voice-Outage
```
→ `WORKAROUND_IN` edge zu `RB-Voice-Outage`

### Keyword Matching
```
KI-Voice-Quality.txt: "voice, routing, latency"
RB-Voice-Diagnostics.txt: "voice, diagnostics, latency"
```
→ `RELATED_TO` edge (2+ gemeinsame Keywords)

### Naming Patterns
```
KI-Voice-Transfer ↔ RB-Voice-Outage
```
→ Similarity 0.5+ → `RELATED_TO` edge

---

## 🎯 CLI Quick Commands

```powershell
# Standard
python scripts/bulk_import_documents.py --zip docs.zip

# Ohne Edges
python scripts/bulk_import_documents.py --zip docs.zip --no-edges

# Höhere Confidence
python scripts/bulk_import_documents.py --zip docs.zip --confidence 0.7

# Verbose
python scripts/bulk_import_documents.py --zip docs.zip --verbose
```

---

## 🌐 REST API

```bash
# Upload
curl -X POST "http://localhost:8000/api/bulk-import/zip" \
  -F "file=@documents.zip" \
  -F "tenant_id=tenant_demo" \
  -F "create_edges=true" \
  -F "min_edge_confidence=0.5"

# Status
curl http://localhost:8000/api/bulk-import/status
```

---

## 📊 Neo4j Queries

```cypher
-- Neue Nodes (letzte Stunde)
MATCH (n {tenant_id: 'tenant_demo'})
WHERE n.created_at > datetime() - duration({hours: 1})
RETURN n

-- Edges mit Confidence
MATCH (a)-[r]->(b)
WHERE r.confidence IS NOT NULL
RETURN a.title, type(r), b.title, r.confidence
ORDER BY r.confidence DESC

-- Orphan Nodes
MATCH (n {tenant_id: 'tenant_demo'})
WHERE NOT (n)--()
RETURN n.title, labels(n)
```

---

## ⚡ Templates

### Known Issue
```
KNOWN ISSUE — KI-{ID}
{Title}

--- WORKAROUND ---
Follow Runbook RB-{ID}

--- REFERENCES ---
- Runbook: RB-{ID}
- FAQ: FAQ-{ID}
```

### Runbook
```
RUNBOOK — RB-{ID}
{Title}

--- STEPS ---
1. {Step}
2. {Step}

--- RELATED ---
- Known Issues: KI-{ID}
```

### FAQ
```
FAQ — FAQ-{ID}
{Question}

--- ANSWER ---
{Answer}

See Runbook RB-{ID} for details.
```

---

## 🐛 Troubleshooting

| Problem | Lösung |
|---------|--------|
| Keine Edges | `--confidence 0.3` |
| Falsche Typen | Naming Convention nutzen |
| UTF-8 Error | `Set-Content -Encoding UTF8` |
| Neo4j Error | `docker-compose up -d neo4j` |

---

## 📖 Vollständige Doku

→ [BULK_IMPORT_GUIDE.md](BULK_IMPORT_GUIDE.md)

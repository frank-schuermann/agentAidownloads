#!/usr/bin/env python3
"""
Known Issues Management Script

Dieses Script demonstriert, wie man Known Issues zum Knowledge Graph hinzufügt.

Usage:
    python add_known_issue.py --method [text|json|neo4j]
    
Examples:
    # Methode 1: Text-Dokument erstellen
    python add_known_issue.py --method text --issue-id KI-2026-020 --title "Chat disconnects" --severity P2
    
    # Methode 2: Static JSON hinzufügen
    python add_known_issue.py --method json --issue-id KI-2026-021 --title "Email delay"
    
    # Methode 3: Neo4j API direkt
    python add_known_issue.py --method neo4j --tenant-id customer_demo --issue-id KI-2026-022
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# -------------------------
# Methode 1: Text-Dokument
# -------------------------
def create_text_document(
    issue_id: str,
    title: str,
    severity: str,
    status: str,
    symptoms: str,
    root_cause: str,
    workaround: str,
    impact: str,
    output_dir: Path,
) -> Path:
    """Erstellt eine strukturierte Text-Datei für Known Issue."""
    
    filename = f"KnownIssue_{issue_id.replace('-', '_')}.txt"
    filepath = output_dir / filename
    
    template = f"""================================================================================
KNOWN ISSUE — {title}
================================================================================

Issue ID     : {issue_id}
Severity     : {severity}
Status       : {status}
Reported     : {datetime.now().strftime('%B %d, %Y')}

AFFECTED:
---------
- Service: <Specify affected service>
- Versions: <Specify versions>
- Regions: <Specify regions if applicable>

SYMPTOMS:
---------
{symptoms}

ROOT CAUSE:
-----------
{root_cause}

IMPACT:
-------
{impact}

WORKAROUND:
-----------
{workaround}

MONITORING:
-----------
<Specify monitoring approach>
- Check: <Metric/Log>
- Alert: <Alert condition>

RESOLUTION TIMELINE:
--------------------
- {datetime.now().strftime('%b %Y')}: Issue identified
- <ETA>: Fix planned
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"✅ Created text document: {filepath}")
    print(f"📝 Next steps:")
    print(f"   1. Edit the file to complete missing sections")
    print(f"   2. Run: python generate_knowledge_graph.py")
    print(f"   3. Verify in knowledge_graph_generated.json")
    
    return filepath


# -------------------------
# Methode 2: Static JSON
# -------------------------
def add_to_static_json(
    issue_id: str,
    title: str,
    severity: str,
    status: str,
    description: str,
    symptoms: str,
    root_cause: str,
    workaround: str,
    impact: str,
    tags: list[str],
    static_nodes_file: Path,
) -> dict:
    """Fügt Known Issue zu static_nodes.json hinzu."""
    
    # Load existing nodes
    if static_nodes_file.exists():
        with open(static_nodes_file, 'r', encoding='utf-8') as f:
            nodes = json.load(f)
    else:
        nodes = []
    
    # Check for duplicates
    if any(n.get('id') == issue_id for n in nodes):
        print(f"⚠️  Issue {issue_id} already exists in static_nodes.json")
        return {}
    
    # Create new node
    new_node = {
        "id": issue_id,
        "type": "KnownIssue",
        "label": title,
        "properties": {
            "issue_id": issue_id,
            "severity": severity,
            "status": status,
            "reported": datetime.now().strftime('%B %d, %Y'),
            "description": description,
            "symptoms": symptoms,
            "root_cause": root_cause,
            "workaround": workaround,
            "impact": impact
        },
        "tags": tags
    }
    
    nodes.append(new_node)
    
    # Save back
    with open(static_nodes_file, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Added {issue_id} to static_nodes.json")
    print(f"📝 Next steps:")
    print(f"   1. Optionally add edges in static_edges.json")
    print(f"   2. Run: python generate_knowledge_graph.py")
    
    return new_node


# -------------------------
# Methode 3: Neo4j API
# -------------------------
def add_via_neo4j(
    tenant_id: str,
    issue_id: str,
    title: str,
    severity: str,
    status: str,
    description: str,
    workaround_summary: str,
    workaround_steps: list[str],
    affected_entities: list[str],
    fixed_in_release_id: Optional[str] = None,
) -> dict:
    """Fügt Known Issue direkt via Neo4j API hinzu."""
    
    try:
        from core.knowledge_graph import KnowledgeGraphService
        from core.knowledge_graph.models.nodes import KnownIssueNode
        from core.knowledge_graph.models.enums import KnownIssueSeverity, KnownIssueStatus
    except ImportError:
        print("❌ Error: core.knowledge_graph module not found")
        print("   Make sure you're running from the project root and Neo4j is configured")
        return {}
    
    # Map severity string to enum
    severity_map = {
        "P0": KnownIssueSeverity.P0,
        "P1": KnownIssueSeverity.P1,
        "P2": KnownIssueSeverity.P2,
        "P3": KnownIssueSeverity.P3,
        "P4": KnownIssueSeverity.P4,
    }
    
    status_map = {
        "Open": KnownIssueStatus.open,
        "Mitigated": KnownIssueStatus.mitigated,
        "Fixed": KnownIssueStatus.fixed,
        "Monitoring": KnownIssueStatus.monitoring,
    }
    
    # Create node
    issue_node = KnownIssueNode(
        tenant_id=tenant_id,
        issue_id=issue_id,
        title=title,
        description=description,
        severity=severity_map.get(severity, KnownIssueSeverity.P2),
        status=status_map.get(status, KnownIssueStatus.open),
        workaround_summary=workaround_summary,
        workaround_steps=workaround_steps,
        fixed_in_release_id=fixed_in_release_id,
        affected_entities=affected_entities,
    )
    
    # Add to graph
    kg = KnowledgeGraphService(tenant_id=tenant_id)
    result = kg.add_known_issue(issue_node)
    
    print(f"✅ Created Known Issue in Neo4j: {issue_id}")
    print(f"📊 Result: {json.dumps(result, indent=2)}")
    print(f"📝 Next steps:")
    print(f"   1. Link to affected services: kg.link_known_issue_affects(...)")
    print(f"   2. Link to workaround docs: kg.link_known_issue_workaround_in(...)")
    print(f"   3. Query: kg.get_known_issue('{issue_id}')")
    
    return result


# -------------------------
# Interactive Mode
# -------------------------
def interactive_mode(method: str) -> dict:
    """Interaktiver Modus für einfache Erstellung."""
    
    print("\n" + "="*80)
    print(f"🚀 Known Issue Creator - Method: {method.upper()}")
    print("="*80 + "\n")
    
    # Common fields
    issue_id = input("Issue ID (e.g., KI-2026-020): ").strip()
    title = input("Title: ").strip()
    severity = input("Severity (P0/P1/P2/P3/P4) [P2]: ").strip() or "P2"
    status = input("Status (Open/Mitigated/Fixed) [Open]: ").strip() or "Open"
    
    print("\nSymptoms (one per line, empty line to finish):")
    symptoms = []
    while True:
        line = input("  - ").strip()
        if not line:
            break
        symptoms.append(line)
    
    root_cause = input("\nRoot Cause: ").strip()
    impact = input("Impact: ").strip()
    
    print("\nWorkaround steps (one per line, empty line to finish):")
    workaround_steps = []
    while True:
        line = input("  - ").strip()
        if not line:
            break
        workaround_steps.append(line)
    
    tags = input("\nTags (comma-separated): ").strip().split(',')
    tags = [t.strip() for t in tags if t.strip()]
    
    # Method-specific
    if method == "text":
        output_dir = Path("Knowledge_Graph_views/data")
        symptoms_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(symptoms)])
        workaround_text = "\n".join([f"  {i+1}. {s}" for i, s in enumerate(workaround_steps)])
        
        return create_text_document(
            issue_id=issue_id,
            title=title,
            severity=severity,
            status=status,
            symptoms=symptoms_text,
            root_cause=root_cause,
            workaround=workaround_text,
            impact=impact,
            output_dir=output_dir,
        )
    
    elif method == "json":
        static_file = Path("Knowledge_Graph_views/static_nodes.json")
        return add_to_static_json(
            issue_id=issue_id,
            title=title,
            severity=severity,
            status=status,
            description=f"{root_cause}. {impact}",
            symptoms="; ".join(symptoms),
            root_cause=root_cause,
            workaround="; ".join(workaround_steps),
            impact=impact,
            tags=tags,
            static_nodes_file=static_file,
        )
    
    elif method == "neo4j":
        tenant_id = input("\nTenant ID: ").strip()
        affected_entities = input("Affected Entities (comma-separated): ").strip().split(',')
        affected_entities = [e.strip() for e in affected_entities if e.strip()]
        fixed_in = input("Fixed in Release ID (optional): ").strip() or None
        
        return add_via_neo4j(
            tenant_id=tenant_id,
            issue_id=issue_id,
            title=title,
            severity=severity,
            status=status,
            description=f"{root_cause}. {impact}",
            workaround_summary="; ".join(workaround_steps),
            workaround_steps=workaround_steps,
            affected_entities=affected_entities,
            fixed_in_release_id=fixed_in,
        )
    
    return {}


# -------------------------
# Main CLI
# -------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Add Known Issues to Knowledge Graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--method',
        choices=['text', 'json', 'neo4j'],
        required=True,
        help='Method to add the known issue'
    )
    
    parser.add_argument('--issue-id', help='Issue ID (e.g., KI-2026-020)')
    parser.add_argument('--title', help='Issue title')
    parser.add_argument('--severity', choices=['P0', 'P1', 'P2', 'P3', 'P4'], default='P2')
    parser.add_argument('--status', choices=['Open', 'Mitigated', 'Fixed'], default='Open')
    parser.add_argument('--tenant-id', help='Tenant ID (for neo4j method)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    if args.interactive or not args.issue_id:
        interactive_mode(args.method)
    else:
        print("❌ Non-interactive mode requires all arguments")
        print("   Use --interactive or -i for guided input")
        parser.print_help()


if __name__ == '__main__':
    main()

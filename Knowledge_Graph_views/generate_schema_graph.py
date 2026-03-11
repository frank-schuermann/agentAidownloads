"""
Knowledge Graph Schema Visualizer
==================================
Generates a meta-knowledge graph that visualizes the schema/ontology
by creating one node per node type and showing the edge rule relationships.

This helps understand the structure and allowed relationships in the knowledge graph.

Usage:
    python generate_schema_graph.py
    Output: knowledge_graph_schema.json
"""

import json
from datetime import datetime
from pathlib import Path


def generate_schema_graph():
    """Generates a schema visualization graph from edge rules."""
    
    # All node types in the schema
    node_types = [
        "Product", "Service", "SPO", "ReleaseNote", "UserGuide",
        "KnownIssue", "Runbook", "SOP", "Incident", "Expert",
        "Team", "Customer", "Infrastructure", "Configuration", 
        "FAQ", "Feature"
    ]
    
    # Edge rules: (source_type, target_type) -> edge_type
    edge_rules = {
        # Product edges
        ("Product", "Service"): "HAS_SERVICE",
        ("Product", "SPO"): "BELONGS_TO_SPO",
        ("Product", "ReleaseNote"): "HAS_RELEASE_NOTE",
        ("Product", "SOP"): "HAS_SOP",
        ("Product", "Feature"): "HAS_FEATURE",
        
        # Service edges
        ("Service", "Infrastructure"): "RUNS_ON",
        ("Service", "Configuration"): "CONFIGURED_BY",
        ("Service", "Service"): "DEPENDS_ON",
        ("Service", "UserGuide"): "DOCUMENTED_IN",
        ("Service", "KnownIssue"): "HAS_KNOWN_ISSUE",
        ("Service", "Runbook"): "HAS_RUNBOOK",
        ("Service", "FAQ"): "HAS_FAQ",
        ("Service", "Feature"): "HAS_FEATURE",
        
        # KnownIssue edges
        ("KnownIssue", "ReleaseNote"): "FIXED_IN",
        ("KnownIssue", "Configuration"): "WORKAROUND_IN",
        ("KnownIssue", "Incident"): "RELATED_TO",
        ("KnownIssue", "Runbook"): "RELATED_TO",
        ("KnownIssue", "UserGuide"): "RELATED_TO",
        ("KnownIssue", "FAQ"): "RELATED_TO",
        
        # Customer edges
        ("Customer", "Incident"): "REPORTED_INCIDENT",
        ("Customer", "SPO"): "SUBSCRIBES_TO",
        
        # Incident edges
        ("Incident", "Service"): "IMPACTED_BY",
        ("Incident", "Runbook"): "RESOLVED_BY",
        ("Incident", "Expert"): "ASSIGNED_TO",
        ("Incident", "KnownIssue"): "RELATED_TO",
        ("Incident", "Configuration"): "RELATED_TO",
        ("Incident", "UserGuide"): "RELATED_TO",
        
        # Runbook edges
        ("Runbook", "Configuration"): "RELATED_TO",
        ("Runbook", "UserGuide"): "RELATED_TO",
        ("Runbook", "KnownIssue"): "RELATED_TO",
        ("Runbook", "SOP"): "RELATED_TO",
        ("Runbook", "Service"): "RELATED_TO",
        
        # UserGuide edges
        ("UserGuide", "KnownIssue"): "RELATED_TO",
        ("UserGuide", "Runbook"): "RELATED_TO",
        ("UserGuide", "Service"): "RELATED_TO",
        
        # ReleaseNote edges
        ("ReleaseNote", "KnownIssue"): "FIXED_IN",
        ("ReleaseNote", "Feature"): "HAS_FEATURE",
        
        # FAQ edges
        ("FAQ", "KnownIssue"): "RELATED_TO",
        ("FAQ", "Runbook"): "RELATED_TO",
        ("FAQ", "Service"): "RELATED_TO",
        ("FAQ", "UserGuide"): "RELATED_TO",
        ("FAQ", "Configuration"): "RELATED_TO",
        
        # Team edges
        ("Team", "Service"): "OWNS",
        ("Team", "Expert"): "ASSIGNED_TO",
        
        # SOP edges
        ("SOP", "Team"): "ESCALATES_TO",
        ("SOP", "Runbook"): "RELATED_TO",
        ("SOP", "KnownIssue"): "RELATED_TO",
        ("SOP", "Service"): "RELATED_TO",
        
        # SPO edges
        ("SPO", "Service"): "HAS_SERVICE",
        ("SPO", "UserGuide"): "RELATED_TO",
        ("SPO", "Feature"): "HAS_FEATURE",
    }
    
    # Node type descriptions and colors
    node_info = {
        "Product": {
            "description": "Top-level product or solution",
            "color": "#22c55e",
            "icon": "📦"
        },
        "Service": {
            "description": "Individual services or components",
            "color": "#60a5fa",
            "icon": "⚙️"
        },
        "SPO": {
            "description": "Service Purchase Order / License",
            "color": "#a78bfa",
            "icon": "📋"
        },
        "ReleaseNote": {
            "description": "Product release notes and updates",
            "color": "#f59e0b",
            "icon": "📝"
        },
        "UserGuide": {
            "description": "Documentation and user guides",
            "color": "#06b6d4",
            "icon": "📖"
        },
        "KnownIssue": {
            "description": "Known bugs and issues",
            "color": "#ef4444",
            "icon": "⚠️"
        },
        "Runbook": {
            "description": "Operational runbooks and procedures",
            "color": "#10b981",
            "icon": "📘"
        },
        "SOP": {
            "description": "Standard Operating Procedures",
            "color": "#8b5cf6",
            "icon": "📑"
        },
        "Incident": {
            "description": "Support incidents and tickets",
            "color": "#f97316",
            "icon": "🚨"
        },
        "Expert": {
            "description": "Subject matter experts",
            "color": "#ec4899",
            "icon": "👤"
        },
        "Team": {
            "description": "Support or development teams",
            "color": "#14b8a6",
            "icon": "👥"
        },
        "Customer": {
            "description": "Customer organizations",
            "color": "#eab308",
            "icon": "🏢"
        },
        "Infrastructure": {
            "description": "Infrastructure components",
            "color": "#64748b",
            "icon": "🖥️"
        },
        "Configuration": {
            "description": "Configuration settings",
            "color": "#94a3b8",
            "icon": "🔧"
        },
        "FAQ": {
            "description": "Frequently asked questions",
            "color": "#06b6d4",
            "icon": "❓"
        },
        "Feature": {
            "description": "Product features",
            "color": "#34d399",
            "icon": "✨"
        }
    }
    
    # Build nodes
    nodes = []
    for node_type in node_types:
        info = node_info.get(node_type, {})
        node = {
            "id": node_type,
            "type": node_type,  # Use actual node type for coloring
            "label": node_type,
            "properties": {
                "description": info.get("description", ""),
                "color": info.get("color", "#64748b"),
                "icon": info.get("icon", "●"),
                "represents": node_type
            },
            "tags": ["Schema", "NodeType"]
        }
        nodes.append(node)
    
    # Build edges from rules
    edges = []
    edge_types_used = set()
    
    for (source_type, target_type), edge_type in edge_rules.items():
        edge = {
            "source": source_type,
            "target": target_type,
            "type": edge_type
        }
        edges.append(edge)
        edge_types_used.add(edge_type)
    
    # Calculate statistics
    edge_type_counts = {}
    for edge in edges:
        edge_type = edge["type"]
        edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
    
    # Build the schema graph
    schema_graph = {
        "metadata": {
            "graph_name": "Knowledge Graph Schema (Ontology)",
            "version": "1.0.0",
            "description": "Meta-graph showing the schema structure and allowed relationships between node types",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "product": "Microsoft Dynamics 365 Contact Center (CCaaS)",
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "schema_version": "v2",
            "generated_by": "generate_schema_graph.py",
            "purpose": "Schema visualization and ontology reference"
        },
        "node_types": ["NodeType"],
        "edge_types": sorted(list(edge_types_used)),
        "nodes": nodes,
        "edges": edges,
        "statistics": {
            "node_types_count": len(node_types),
            "edge_rules_count": len(edge_rules),
            "edge_type_usage": edge_type_counts
        },
        "ai_agent_instructions": {
            "purpose": "This schema graph shows the ontology/structure of the knowledge graph. Each node represents a node type, and edges show allowed relationships.",
            "usage": [
                "Use this to understand the knowledge graph structure",
                "Identify valid relationship paths between node types",
                "Discover which node types connect to which",
                "Plan graph traversal strategies",
                "Validate edge type usage"
            ]
        }
    }
    
    return schema_graph


def main():
    """Main function."""
    print("=" * 70)
    print("Knowledge Graph Schema Generator")
    print("=" * 70)
    
    # Generate the schema graph
    print("\n📊 Generating schema graph...")
    schema_graph = generate_schema_graph()
    
    # Output file
    output_file = Path(__file__).parent / "knowledge_graph_schema.json"
    
    # Save to file
    print(f"💾 Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(schema_graph, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n✅ Schema graph generated successfully!")
    print(f"   📍 Output: {output_file}")
    print(f"   📦 Node types: {schema_graph['metadata']['total_nodes']}")
    print(f"   🔗 Edge rules: {schema_graph['metadata']['total_edges']}")
    print(f"   🏷️  Edge types: {len(schema_graph['edge_types'])}")
    
    print("\n🎨 Node Types in Schema:")
    for node in schema_graph['nodes']:
        icon = node['properties'].get('icon', '')
        label = node['label']
        desc = node['properties'].get('description', '')
        print(f"   {icon} {label:20} - {desc}")
    
    print(f"\n🔗 Most Used Edge Types:")
    edge_counts = schema_graph['statistics']['edge_type_usage']
    top_edges = sorted(edge_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for edge_type, count in top_edges:
        print(f"   {edge_type:25} ({count} connections)")
    
    print("\n" + "=" * 70)
    print("🌐 Open graph_explorer.html and select 'knowledge_graph_schema.json'")
    print("   to visualize the schema structure!")
    print("=" * 70)


if __name__ == "__main__":
    main()

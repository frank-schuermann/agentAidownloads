#!/usr/bin/env python3
"""
Bulk Document Import - Interactive CLI

Imports documents from ZIP archives into the Knowledge Graph
with intelligent edge inference.

Usage:
    python scripts/bulk_import_documents.py --zip documents.zip
    python scripts/bulk_import_documents.py --zip docs.zip --no-edges
    python scripts/bulk_import_documents.py --zip docs.zip --confidence 0.7
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.knowledge_graph.bulk_import_service import BulkImportService


def main():
    parser = argparse.ArgumentParser(
        description="Bulk import documents from ZIP archive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic import
  python scripts/bulk_import_documents.py --zip documents.zip

  # Import without edge inference
  python scripts/bulk_import_documents.py --zip docs.zip --no-edges

  # Custom confidence threshold
  python scripts/bulk_import_documents.py --zip docs.zip --confidence 0.7

  # Different tenant
  python scripts/bulk_import_documents.py --zip docs.zip --tenant my_tenant
        """
    )
    
    parser.add_argument(
        '--zip',
        type=Path,
        required=True,
        help="Path to ZIP file with documents"
    )
    
    parser.add_argument(
        '--tenant',
        type=str,
        default="tenant_demo",
        help="Tenant ID (default: tenant_demo)"
    )
    
    parser.add_argument(
        '--no-edges',
        action='store_true',
        help="Skip edge inference (only create nodes)"
    )
    
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.5,
        help="Minimum edge confidence threshold (0.0-1.0, default: 0.5)"
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate ZIP file
    if not args.zip.exists():
        print(f"❌ Error: File not found: {args.zip}")
        sys.exit(1)
    
    if not args.zip.suffix.lower() == '.zip':
        print(f"❌ Error: File must be a ZIP archive: {args.zip}")
        sys.exit(1)
    
    # Validate confidence
    if not 0.0 <= args.confidence <= 1.0:
        print(f"❌ Error: Confidence must be between 0.0 and 1.0")
        sys.exit(1)
    
    # Print header
    print("=" * 80)
    print("🚀 Bulk Document Import - Knowledge Graph")
    print("=" * 80)
    print(f"📁 ZIP File:     {args.zip}")
    print(f"🏢 Tenant:       {args.tenant}")
    print(f"🔗 Create Edges: {'No' if args.no_edges else 'Yes'}")
    print(f"📊 Min Confidence: {args.confidence}")
    print("=" * 80)
    print()
    
    # Import
    try:
        service = BulkImportService(args.tenant)
        
        print("⏳ Importing documents...")
        
        result = service.import_from_zip(
            zip_path=str(args.zip),
            create_edges=not args.no_edges,
            min_edge_confidence=args.confidence,
        )
        
        # Print results
        print("\n" + "=" * 80)
        print("✅ Import Completed")
        print("=" * 80)
        
        stats = result["stats"]
        
        print(f"\n📊 Statistics:")
        print(f"   Files Processed:  {stats['files_processed']}")
        print(f"   Nodes Created:    {stats['nodes_created']}")
        print(f"   Edges Created:    {stats['edges_created']}")
        print(f"   Errors:           {len(stats['errors'])}")
        
        if stats['errors'] and args.verbose:
            print(f"\n⚠️  Errors:")
            for error in stats['errors']:
                print(f"   - {error}")
        
        print(f"\n🕐 Timestamp: {result['timestamp']}")
        print()
        
        # Save report
        report_path = args.zip.parent / f"import_report_{args.tenant}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Full report saved: {report_path}")
        print()
        
    except Exception as e:
        print(f"\n❌ Import Failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

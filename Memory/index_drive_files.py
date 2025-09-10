"""
Command-line utility to index Google Drive files into the dual memory RBAC system
"""

import sys
import os
import asyncio
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Memory.automatic_file_indexer import run_automatic_indexing

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Main function to run file indexing"""
    
    # Get user ID from command line or use default
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        user_id = input("Enter user ID (or press Enter for 'demo-admin-001'): ").strip()
        if not user_id:
            user_id = "demo-admin-001"
    
    print(f"\n🚀 Starting automatic file indexing for user: {user_id}")
    print("This will scan your DigitalTwin_Brain Google Drive folder and index all files...")
    
    try:
        # Run the indexing
        results = await run_automatic_indexing(user_id)
        
        # Display results
        print("\n" + "="*70)
        print("📊 AUTOMATIC FILE INDEXING RESULTS")
        print("="*70)
        print(f"✅ Public files indexed: {results['public_files_indexed']}")
        print(f"🔒 Private files indexed: {results['private_files_indexed']}")
        print(f"⏭️  Skipped files: {results['skipped_files']}")
        print(f"❌ Errors: {results['errors']}")
        
        total_indexed = results['public_files_indexed'] + results['private_files_indexed']
        print(f"\n📈 Total files indexed: {total_indexed}")
        
        if results['file_details']:
            print(f"\n📋 FILE DETAILS:")
            for detail in results['file_details'][:10]:  # Show first 10
                file_type = "🔒 Private" if detail['type'] == 'private' else "📁 Public"
                print(f"  {file_type}: {detail['file']} → {detail['agent']} ({detail['department']})")
            
            if len(results['file_details']) > 10:
                print(f"  ... and {len(results['file_details']) - 10} more files")
        
        if results['errors'] > 0:
            print(f"\n⚠️  {results['errors']} errors occurred. Check the logs for details.")
        
        print("\n🎉 File indexing complete! Your agents can now access the information in these files.")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error during file indexing: {e}")
        logger.exception("Full error details:")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)






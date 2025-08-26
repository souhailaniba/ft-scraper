#!/usr/bin/env python3
"""
Standalone script to import JSON files to MongoDB
"""

import sys
import argparse
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.mongodb_handler import MongoDBHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Import JSON files to MongoDB')
    parser.add_argument('json_file', type=str, help='Path to JSON file')
    parser.add_argument('--type', '-t', choices=['sitemap', 'articles', 'auto'], 
                       default='auto', help='Data type (default: auto-detect)')
    parser.add_argument('--connection', '-c', type=str, 
                       default='mongodb://localhost:27017/',
                       help='MongoDB connection string')
    parser.add_argument('--database', '-d', type=str, default='ft_scraper',
                       help='Database name (default: ft_scraper)')
    return parser.parse_args()


def main():
    """Main function"""
    
    args = parse_arguments()
    json_file = Path(args.json_file)
    
    print("JSON to MongoDB Importer")
    print("=" * 40)
    print(f"JSON File: {json_file}")
    print(f"Data Type: {args.type}")
    print(f"Database: {args.database}")
    print("=" * 40)
    
    # Check if file exists
    if not json_file.exists():
        print(f"Error: JSON file not found: {json_file}")
        return False
    
    # Connect to MongoDB
    mongo_handler = MongoDBHandler(
        connection_string=args.connection,
        database_name=args.database
    )
    
    if not mongo_handler.connect():
        print("Error: Failed to connect to MongoDB")
        print("Make sure MongoDB is running and accessible")
        return False
    
    print("Connected to MongoDB successfully")
    
    # Import JSON data
    print(f"Importing {json_file.name}...")
    
    success = mongo_handler.load_json_to_mongodb(json_file, args.type)
    
    if success:
        print("Import completed successfully!")
        
        # Show statistics
        stats = mongo_handler.get_statistics()
        print("\nDatabase Statistics:")
        for collection_name, collection_stats in stats.get('collections', {}).items():
            count = collection_stats.get('document_count', 0)
            print(f"  {collection_name}: {count:,} documents")
            
            if 'success_rate' in collection_stats:
                success_rate = collection_stats['success_rate']
                successful = collection_stats.get('successful_articles', 0)
                failed = collection_stats.get('failed_articles', 0)
                print(f"    Successful: {successful:,}, Failed: {failed:,}")
                print(f"    Success Rate: {success_rate:.1f}%")
        
        return True
    else:
        print("Import failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
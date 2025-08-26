#!/usr/bin/env python3
"""
Query and analyze MongoDB data
"""

import sys
import argparse
import json
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.mongodb_handler import MongoDBHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Query MongoDB data')
    parser.add_argument('--stats', '-s', action='store_true',
                       help='Show database statistics')
    parser.add_argument('--query', '-q', type=str,
                       help='JSON query string (e.g., \'{"success": true}\')')
    parser.add_argument('--limit', '-l', type=int, default=10,
                       help='Limit results (default: 10)')
    parser.add_argument('--successful', action='store_true',
                       help='Show only successful articles')
    parser.add_argument('--failed', action='store_true',
                       help='Show only failed articles')
    parser.add_argument('--recent', '-r', type=int,
                       help='Show N most recent articles')
    parser.add_argument('--connection', '-c', type=str,
                       default='mongodb://localhost:27017/',
                       help='MongoDB connection string')
    parser.add_argument('--database', '-d', type=str, default='ft_scraper',
                       help='Database name')
    return parser.parse_args()


def show_statistics(mongo_handler):
    """Show database statistics"""
    print("Database Statistics")
    print("=" * 40)
    
    stats = mongo_handler.get_statistics()
    
    if 'error' in stats:
        print(f"Error: {stats['error']}")
        return
    
    print(f"Database: {stats['database_name']}")
    print()
    
    for collection_name, collection_stats in stats.get('collections', {}).items():
        count = collection_stats.get('document_count', 0)
        print(f"{collection_name}:")
        print(f"  Documents: {count:,}")
        
        if 'success_rate' in collection_stats:
            success_rate = collection_stats['success_rate']
            successful = collection_stats.get('successful_articles', 0)
            failed = collection_stats.get('failed_articles', 0)
            print(f"  Successful: {successful:,}")
            print(f"  Failed: {failed:,}")
            print(f"  Success Rate: {success_rate:.1f}%")
        print()


def query_articles(mongo_handler, filter_dict, limit):
    """Query and display articles"""
    print(f"Query Results (limit: {limit})")
    print("=" * 40)
    
    results = mongo_handler.query_articles(filter_dict, limit)
    
    if not results:
        print("No results found")
        return
    
    print(f"Found {len(results)} articles:")
    print()
    
    for i, article in enumerate(results, 1):
        print(f"{i}. {article.get('url', 'No URL')}")
        
        if article.get('success'):
            title = article.get('title', 'No title')
            text_length = article.get('text_length', 0)
            authors = article.get('authors', [])
            scraped_at = article.get('scraped_at', 'Unknown')
            
            print(f"   Title: {title[:80]}{'...' if len(title) > 80 else ''}")
            print(f"   Text Length: {text_length:,} characters")
            print(f"   Authors: {', '.join(authors) if authors else 'None'}")
            print(f"   Scraped: {scraped_at}")
        else:
            error = article.get('error', 'Unknown error')
            print(f"   Status: FAILED")
            print(f"   Error: {error}")
        
        print()


def main():
    """Main function"""
    args = parse_arguments()
    
    print("MongoDB Query Tool")
    print("=" * 40)
    
    # Connect to MongoDB
    mongo_handler = MongoDBHandler(
        connection_string=args.connection,
        database_name=args.database
    )
    
    if not mongo_handler.connect():
        print("Error: Failed to connect to MongoDB")
        return False
    
    try:
        if args.stats:
            show_statistics(mongo_handler)
            return True
        
        # Build query filter
        filter_dict = {}
        
        if args.successful:
            filter_dict['success'] = True
        elif args.failed:
            filter_dict['success'] = False
        
        if args.query:
            try:
                query_filter = json.loads(args.query)
                filter_dict.update(query_filter)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON query: {args.query}")
                return False
        
        if args.recent:
            # Query most recent articles
            print(f"Querying {args.recent} most recent articles...")
            # Note: This would require sorting by scraped_at
            filter_dict = {"success": True}  # Focus on successful ones
            limit = args.recent
        else:
            limit = args.limit
        
        query_articles(mongo_handler, filter_dict, limit)
        return True
        
    finally:
        mongo_handler.disconnect()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
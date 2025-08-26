"""
MongoDB handler for FT Scraper data storage
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, BulkWriteError
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from .logger import get_logger

logger = get_logger(__name__)


class MongoDBHandler:
    """MongoDB operations handler for FT scraper data"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", 
                 database_name: str = "ft_scraper"):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection string
            database_name: Database name to use
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None
        
        # Collection names
        self.collections = {
            'sitemap_data': 'sitemap_data',
            'scraped_articles': 'scraped_articles',
            'scraping_sessions': 'scraping_sessions'
        }
    
    def connect(self) -> bool:
        """
        Connect to MongoDB
        
        Returns:
            True if connection successful
        """
        try:
            self.client = MongoClient(self.connection_string)
            # Test connection
            self.client.admin.command('ismaster')
            self.db = self.client[self.database_name]
            
            logger.info(f"Connected to MongoDB: {self.database_name}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected"""
        try:
            if self.client:
                self.client.admin.command('ismaster')
                return True
        except Exception:
            pass
        return False
    
    def save_sitemap_data(self, data: List[Dict[str, Any]], 
                         batch_size: int = 1000) -> bool:
        """
        Save sitemap data to MongoDB
        
        Args:
            data: List of sitemap entries
            batch_size: Number of documents to insert per batch
            
        Returns:
            Success status
        """
        if not self.is_connected():
            logger.error("Not connected to MongoDB")
            return False
        
        try:
            collection = self.db[self.collections['sitemap_data']]
            
            # Create indexes for efficient queries
            collection.create_index("loc", unique=True)
            collection.create_index("lastmod")
            collection.create_index("sitemap")
            
            # Import proper PyMongo operations
            from pymongo import UpdateOne
            
            # Process data in batches
            total_inserted = 0
            total_updated = 0
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                # Prepare upsert operations using proper PyMongo format
                operations = []
                for item in batch:
                    operation = UpdateOne(
                        filter={"loc": item["loc"]},
                        update={"$set": {
                            **item,
                            "inserted_at": datetime.utcnow(),
                            "data_type": "sitemap_entry"
                        }},
                        upsert=True
                    )
                    operations.append(operation)
                
                # Execute bulk operations
                if operations:
                    result = collection.bulk_write(operations, ordered=False)
                    total_inserted += result.upserted_count
                    total_updated += result.modified_count
            
            logger.info(f"Sitemap data saved: {total_inserted} inserted, {total_updated} updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save sitemap data: {e}")
            return False
    
    def save_scraped_articles(self, data: List[Dict[str, Any]], 
                             session_id: Optional[str] = None) -> bool:
        """
        Save scraped articles to MongoDB
        
        Args:
            data: List of scraped article entries
            session_id: Optional session identifier
            
        Returns:
            Success status
        """
        if not self.is_connected():
            logger.error("Not connected to MongoDB")
            return False
        
        try:
            collection = self.db[self.collections['scraped_articles']]
            
            # Create indexes
            collection.create_index("url", unique=True)
            collection.create_index("success")
            collection.create_index("scraped_at")
            collection.create_index("text_length")
            
            # Add session metadata
            if not session_id:
                session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
            # Prepare documents with proper format
            documents = []
            for item in data:
                doc = {
                    **item,
                    "session_id": session_id,
                    "inserted_at": datetime.utcnow(),
                    "data_type": "scraped_article"
                }
                documents.append(doc)
            
            # Use proper PyMongo bulk operations
            from pymongo import UpdateOne
            
            operations = []
            for doc in documents:
                operation = UpdateOne(
                    filter={"url": doc["url"]},
                    update={"$set": doc},
                    upsert=True
                )
                operations.append(operation)
            
            result = collection.bulk_write(operations, ordered=False)
            
            # Log session summary
            self._log_scraping_session(session_id, data)
            
            logger.info(f"Scraped articles saved: {result.upserted_count} new, {result.modified_count} updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save scraped articles: {e}")
            return False
    
    def _log_scraping_session(self, session_id: str, data: List[Dict[str, Any]]):
        """Log scraping session metadata"""
        try:
            collection = self.db[self.collections['scraping_sessions']]
            
            # Calculate session statistics
            successful = len([item for item in data if item.get('success', False)])
            failed = len(data) - successful
            total_chars = sum(item.get('text_length', 0) for item in data if item.get('success', False))
            
            session_doc = {
                "session_id": session_id,
                "started_at": datetime.utcnow(),
                "total_articles": len(data),
                "successful": successful,
                "failed": failed,
                "success_rate": (successful / len(data) * 100) if data else 0,
                "total_characters": total_chars,
                "average_chars": total_chars // successful if successful > 0 else 0
            }
            
            collection.insert_one(session_doc)
            
        except Exception as e:
            logger.error(f"Failed to log session: {e}")
    
    def load_json_to_mongodb(self, json_file_path: Path, 
                            data_type: str = "auto") -> bool:
        """
        Load JSON file into appropriate MongoDB collection
        
        Args:
            json_file_path: Path to JSON file
            data_type: Type of data ('sitemap', 'articles', or 'auto')
            
        Returns:
            Success status
        """
        if not json_file_path.exists():
            logger.error(f"JSON file not found: {json_file_path}")
            return False
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                logger.warning(f"No data in JSON file: {json_file_path}")
                return False
            
            # Auto-detect data type if not specified
            if data_type == "auto":
                sample_item = data[0] if isinstance(data, list) else data
                if 'success' in sample_item and 'text' in sample_item:
                    data_type = "articles"
                elif 'loc' in sample_item and 'sitemap' in sample_item:
                    data_type = "sitemap"
                else:
                    logger.error("Cannot auto-detect data type")
                    return False
            
            # Route to appropriate save method
            if data_type == "sitemap":
                return self.save_sitemap_data(data)
            elif data_type == "articles":
                session_id = f"json_import_{json_file_path.stem}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                return self.save_scraped_articles(data, session_id)
            else:
                logger.error(f"Unknown data type: {data_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load JSON file: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.is_connected():
            return {"error": "Not connected to MongoDB"}
        
        try:
            stats = {
                "database_name": self.database_name,
                "collections": {}
            }
            
            for collection_name in self.collections.values():
                if collection_name in self.db.list_collection_names():
                    collection = self.db[collection_name]
                    count = collection.count_documents({})
                    stats["collections"][collection_name] = {
                        "document_count": count
                    }
                    
                    # Additional stats for specific collections
                    if collection_name == "scraped_articles":
                        successful = collection.count_documents({"success": True})
                        failed = collection.count_documents({"success": False})
                        stats["collections"][collection_name].update({
                            "successful_articles": successful,
                            "failed_articles": failed,
                            "success_rate": (successful / count * 100) if count > 0 else 0
                        })
                else:
                    stats["collections"][collection_name] = {"document_count": 0}
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}
    
    def query_articles(self, filter_dict: Dict[str, Any] = None, 
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query scraped articles
        
        Args:
            filter_dict: MongoDB filter dictionary
            limit: Maximum number of results
            
        Returns:
            List of matching articles
        """
        if not self.is_connected():
            return []
        
        try:
            collection = self.db[self.collections['scraped_articles']]
            filter_dict = filter_dict or {}
            
            cursor = collection.find(filter_dict).limit(limit)
            results = list(cursor)
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                if '_id' in result:
                    result['_id'] = str(result['_id'])
            
            return results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
"""
File handling utilities for FT Scraper
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from .logger import get_logger

logger = get_logger(__name__)


class FileHandler:
    """File operations handler for JSON and other data formats"""
    
    @staticmethod
    def save_json(data: Any, filepath: Path, indent: int = 2) -> bool:
        """
        Save data to JSON file
        
        Args:
            data: Data to save
            filepath: Path to save file
            indent: JSON indentation
            
        Returns:
            Success status
        """
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Custom JSON encoder to handle pandas Timestamps and NaN values
            import pandas as pd
            import numpy as np
            
            def clean_data(obj):
                """Recursively clean data, converting NaN to None"""
                if isinstance(obj, dict):
                    return {key: clean_data(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [clean_data(item) for item in obj]
                elif pd.isna(obj) or (isinstance(obj, float) and np.isnan(obj)):
                    return None
                else:
                    return obj
            
            class TimestampEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, pd.Timestamp):
                        return obj.strftime('%Y-%m-%d %H:%M:%S UTC')
                    elif pd.isna(obj):
                        return None
                    return super().default(obj)
            
            # Clean the data before saving
            clean_data_obj = clean_data(data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(clean_data_obj, f, indent=indent, ensure_ascii=False, cls=TimestampEncoder)
            
            logger.info(f"Saved data to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save JSON to {filepath}: {e}")
            return False
    
    @staticmethod
    def load_json(filepath: Path) -> Optional[Any]:
        """
        Load data from JSON file
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Loaded data or None if failed
        """
        try:
            if not filepath.exists():
                logger.error(f"File not found: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Loaded data from {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load JSON from {filepath}: {e}")
            return None
    
    @staticmethod
    def save_checkpoint(data: List[Dict], filepath: Path) -> bool:
        """
        Save checkpoint data
        
        Args:
            data: Checkpoint data
            filepath: Checkpoint file path
            
        Returns:
            Success status
        """
        try:
            checkpoint_path = filepath.parent / f"checkpoint_{filepath.stem}.json"
            return FileHandler.save_json(data, checkpoint_path)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    @staticmethod
    def get_file_stats(filepath: Path) -> Dict[str, Any]:
        """
        Get file statistics
        
        Args:
            filepath: Path to file
            
        Returns:
            File statistics
        """
        try:
            if not filepath.exists():
                return {"exists": False}
            
            stat = filepath.stat()
            return {
                "exists": True,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": stat.st_mtime
            }
        except Exception as e:
            logger.error(f"Failed to get file stats for {filepath}: {e}")
            return {"exists": False, "error": str(e)}
    
    @staticmethod
    def analyze_json_data(data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze JSON data structure
        
        Args:
            data: JSON data list
            
        Returns:
            Analysis results
        """
        if not data:
            return {"total_count": 0}
        
        try:
            total_count = len(data)
            successful = len([item for item in data if item.get('success', False)])
            failed = total_count - successful
            
            # Calculate text statistics for successful items
            text_lengths = [
                len(item.get('text', '')) 
                for item in data 
                if item.get('success', False) and item.get('text')
            ]
            
            total_chars = sum(text_lengths)
            avg_chars = total_chars // len(text_lengths) if text_lengths else 0
            
            return {
                "total_count": total_count,
                "successful": successful,
                "failed": failed,
                "success_rate": round(successful / total_count * 100, 1) if total_count > 0 else 0,
                "total_characters": total_chars,
                "average_chars_per_article": avg_chars
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze data: {e}")
            return {"error": str(e)}
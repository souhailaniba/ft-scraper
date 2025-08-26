"""
Date utilities for article filtering and processing
"""

import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from dateutil import parser as date_parser
from .logger import get_logger

logger = get_logger(__name__)


class DateExtractor:
    """Enhanced date extraction and filtering utilities"""
    
    def __init__(self):
        """Initialize date extractor with common date patterns"""
        self.date_patterns = [
            # Standard formats
            r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',  # YYYY-MM-DD
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b',  # MM-DD-YYYY or DD-MM-YYYY
            
            # Written formats
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})\b',
            
            # European formats
            r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
            r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{4})\b',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.date_patterns]
    
    def parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse various timestamp formats to datetime"""
        if not timestamp:
            return None
        
        try:
            # Handle string timestamps from new format
            if isinstance(timestamp, str):
                if 'UTC' in timestamp:
                    # Parse "1995-11-18 02:01:30 UTC" format
                    return datetime.strptime(timestamp.replace(' UTC', ''), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                else:
                    # Try to parse other string formats
                    return date_parser.parse(timestamp)
            
            # Handle numeric timestamps (milliseconds)
            elif isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                
        except (ValueError, OSError, TypeError) as e:
            logger.debug(f"Failed to parse timestamp {timestamp}: {e}")
        
        return None
    
    def extract_year_month(self, item: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        """Extract year and month from article item"""
        # Method 1: From sitemap filename
        sitemap = item.get('sitemap', '')
        if 'archive-' in sitemap:
            try:
                # Extract from patterns like "archive-2025-8.xml"
                parts = sitemap.split('archive-')[1].split('-')
                year = int(parts[0])
                month = int(parts[1].split('.')[0]) if len(parts) > 1 else None
                return year, month
            except (IndexError, ValueError):
                pass
        
        # Method 2: From lastmod timestamp
        if item.get('lastmod'):
            dt = self.parse_timestamp(item['lastmod'])
            if dt:
                return dt.year, dt.month
        
        return None, None
    
    def filter_by_current_month(self, articles: list, target_year: int = None, target_month: int = None) -> list:
        """Filter articles to current month only"""
        if not target_year or not target_month:
            now = datetime.now()
            target_year = target_year or now.year
            target_month = target_month or now.month
        
        filtered_articles = []
        
        for article in articles:
            year, month = self.extract_year_month(article)
            
            if year == target_year and month == target_month:
                filtered_articles.append(article)
        
        logger.info(f"Filtered to {len(filtered_articles)} articles from {target_year}-{target_month:02d}")
        return filtered_articles
    
    def prioritize_by_lastmod(self, articles: list) -> list:
        """Sort articles by last modified date (newest first)"""
        def get_lastmod_timestamp(article):
            dt = self.parse_timestamp(article.get('lastmod'))
            return dt.timestamp() if dt else 0
        
        sorted_articles = sorted(articles, key=get_lastmod_timestamp, reverse=True)
        logger.info(f"Prioritized {len(sorted_articles)} articles by last modified date")
        return sorted_articles
    
    def extract_dates_from_text(self, text: str) -> list:
        """Extract dates from article text content"""
        if not text:
            return []
        
        found_dates = []
        
        for pattern in self.compiled_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                try:
                    # Try to parse the matched text as a date
                    date_str = match.group(0)
                    parsed_date = date_parser.parse(date_str, fuzzy=False)
                    
                    found_dates.append({
                        'date_string': date_str,
                        'parsed_date': parsed_date.isoformat(),
                        'position': match.start()
                    })
                except (ValueError, date_parser.ParserError):
                    continue
        
        # Remove duplicates and sort by position in text
        unique_dates = {}
        for date_info in found_dates:
            key = date_info['parsed_date']
            if key not in unique_dates or date_info['position'] < unique_dates[key]['position']:
                unique_dates[key] = date_info
        
        result = list(unique_dates.values())
        result.sort(key=lambda x: x['position'])
        
        if result:
            logger.debug(f"Extracted {len(result)} dates from article text")
        
        return result
    
    def get_article_publication_date(self, article_data: Dict[str, Any]) -> Optional[datetime]:
        """Get the best available publication date for an article"""
        # Priority order: extracted dates > newspaper4k publish_date > lastmod
        
        # 1. Try extracted dates from text
        if article_data.get('extracted_dates'):
            try:
                # Use the first (earliest in text) date
                first_date = article_data['extracted_dates'][0]['parsed_date']
                return datetime.fromisoformat(first_date.replace('Z', '+00:00'))
            except (ValueError, IndexError):
                pass
        
        # 2. Try newspaper4k publish_date
        if article_data.get('publish_date'):
            try:
                return datetime.fromisoformat(article_data['publish_date'].replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # 3. Fall back to lastmod
        if article_data.get('lastmod'):
            return self.parse_timestamp(article_data['lastmod'])
        
        return None


def get_current_month_articles(articles: list, year: int = None, month: int = None) -> list:
    """Convenience function to filter articles by current month"""
    extractor = DateExtractor()
    return extractor.filter_by_current_month(articles, year, month)


def prioritize_by_recency(articles: list) -> list:
    """Convenience function to prioritize articles by recency"""
    extractor = DateExtractor()
    return extractor.prioritize_by_lastmod(articles)
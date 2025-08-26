"""
Article scraper for FT.com using Node.js API
"""

import json
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from config.settings import (
    API_URL, DEFAULT_MAX_WORKERS, DEFAULT_REQUEST_TIMEOUT, 
    DEFAULT_DELAY_BETWEEN_REQUESTS, CHECKPOINT_FREQUENCY, MIN_ARTICLE_YEAR
)
from src.utils.logger import get_logger
from src.utils.file_handler import FileHandler
from src.extractors.text_extractor import TextExtractor

logger = get_logger(__name__, 'article_scraper.log')


class ArticleScraper:
    """Article scraper for FT.com using Node.js API backend"""
    
    def __init__(self, api_url: str = API_URL, max_workers: int = DEFAULT_MAX_WORKERS):
        """
        Initialize article scraper
        
        Args:
            api_url: Node.js API URL
            max_workers: Maximum number of worker threads
        """
        self.api_url = api_url
        self.max_workers = max_workers
        self.session = requests.Session()
        self.text_extractor = TextExtractor()
        self.file_handler = FileHandler()
        self.lock = threading.Lock()
        
        logger.info(f"Article scraper initialized - API: {api_url}, Workers: {max_workers}")
    
    def check_api_health(self) -> bool:
        """
        Check if the Node.js API is running and ready
        
        Returns:
            True if API is healthy
        """
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                is_ready = health_data.get('browserReady', False)
                
                if is_ready:
                    logger.info("API health check passed")
                else:
                    logger.warning("API is running but browser is not ready")
                
                return is_ready
            else:
                logger.error(f"API health check failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Cannot connect to API: {e}")
            return False
    
    def scrape_article_html(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get HTML content from Node.js API
        
        Args:
            url: Article URL to scrape
            
        Returns:
            API response dict or None if failed
        """
        try:
            response = self.session.post(
                f"{self.api_url}/scrape",
                json={"url": url},
                timeout=DEFAULT_REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error for {url}: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def process_single_article(self, article_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single article: scrape HTML and extract text
        
        Args:
            article_info: Article information dictionary
            
        Returns:
            Processing result dictionary
        """
        url = article_info['url']
        thread_id = threading.current_thread().ident
        
        # Log processing start
        date_info = article_info.get('article_date', 'Unknown date')
        if isinstance(date_info, str):
            date_str = date_info
        else:
            date_str = date_info.strftime('%Y-%m-%d') if date_info else 'Unknown'
        
        logger.info(f"[Thread {thread_id}] Processing: {url} ({date_str})")
        
        try:
            # Step 1: Get HTML from API
            api_response = self.scrape_article_html(url)
            if not api_response or not api_response.get('success'):
                return self._create_failed_result(
                    article_info, 
                    'Failed to get HTML from API',
                    api_response.get('error', 'Unknown API error') if api_response else 'No API response'
                )
            
            html_content = api_response.get('html', '')
            if not html_content:
                return self._create_failed_result(article_info, 'Empty HTML content from API')
            
            # Step 2: Extract text with newspaper4k
            extracted_data = self.text_extractor.extract_from_html(html_content, url)
            
            # Step 3: Check if extraction failed (matching original logic)
            if (not extracted_data or 
                extracted_data.get('text') == 'No text extracted' or
                extracted_data.get('text', '').startswith('Failed to extract text:')):
                return self._create_failed_result(
                    article_info, 
                    'Failed to extract meaningful text with newspaper4k',
                    f"Text: {extracted_data.get('text', 'None')[:100]}..." if extracted_data else 'No extraction data'
                )
            
            # Step 4: Create successful result
            result = self._create_successful_result(article_info, extracted_data)
            
            logger.info(f"[Thread {thread_id}] Success: {url} ({result['text_length']} chars, {date_str})")
            return result
            
        except Exception as e:
            logger.error(f"[Thread {thread_id}] Error processing {url}: {e}")
            return self._create_failed_result(article_info, 'Processing exception', str(e))
    
    def _create_successful_result(self, article_info: Dict[str, Any], extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create successful processing result"""
        # Convert datetime objects to strings for JSON serialization
        article_date = article_info.get('article_date')
        if hasattr(article_date, 'isoformat'):
            article_date = article_date.isoformat()
        
        return {
            'url': article_info['url'],
            'article_date': article_date,
            'success': True,
            'title': extracted_data['title'],
            'text': extracted_data['text'],
            'authors': extracted_data['authors'],
            'publish_date': extracted_data['publish_date'],
            'top_image': extracted_data['top_image'],
            'summary': extracted_data.get('summary'),
            'lastmod': article_info.get('lastmod'),
            'sitemap': article_info.get('sitemap'),
            'scraped_at': datetime.now().isoformat(),
            'text_length': extracted_data['text_length']
        }
    
    def _create_failed_result(self, article_info: Dict[str, Any], error_type: str, details: str = '') -> Dict[str, Any]:
        """Create failed processing result"""
        # Convert datetime objects to strings for JSON serialization
        article_date = article_info.get('article_date')
        if hasattr(article_date, 'isoformat'):
            article_date = article_date.isoformat()
            
        return {
            'url': article_info['url'],
            'article_date': article_date,
            'success': False,
            'error': error_type,
            'error_details': details,
            'scraped_at': datetime.now().isoformat()
        }
    
    def load_article_urls(self, filepath: Path, min_year: int = MIN_ARTICLE_YEAR, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load and filter article URLs from sitemap data
        
        Args:
            filepath: Path to sitemap JSON file
            min_year: Minimum article year to include
            limit: Maximum number of articles to load
            
        Returns:
            List of article information dictionaries
        """
        logger.info(f"Loading article URLs from {filepath}")
        
        # Load raw sitemap data
        raw_data = self.file_handler.load_json(filepath)
        if not raw_data:
            logger.error("Failed to load sitemap data")
            return []
        
        # Filter and process articles
        articles = []
        for item in raw_data:
            if not item.get('loc') or item.get('errors'):
                continue
            
            # Extract year information
            year = self._extract_article_year(item)
            if year and year >= min_year:
                articles.append({
                    'url': item['loc'],
                    'year': year,
                    'article_date': self._parse_article_date(item),
                    'lastmod': item.get('lastmod'),
                    'sitemap': item.get('sitemap'),
                    'has_image': bool(item.get('image_loc'))
                })
        
        # Sort by year (newest first)
        articles.sort(key=lambda x: x['year'], reverse=True)
        
        # Apply limit if specified
        if limit:
            articles = articles[:limit]
        
        logger.info(f"Loaded {len(articles)} articles from {min_year}+ (total processed: {len(raw_data)})")
        return articles
    
    def _extract_article_year(self, item: Dict[str, Any]) -> Optional[int]:
        """Extract year from article item (handles both original and new formats)"""
        # Method 1: From sitemap filename
        sitemap = item.get('sitemap', '')
        if 'archive-' in sitemap:
            try:
                year_part = sitemap.split('archive-')[1].split('-')[0]
                return int(year_part)
            except (IndexError, ValueError):
                pass
        
        # Method 2: From lastmod timestamp
        if item.get('lastmod'):
            try:
                timestamp = item['lastmod']
                
                # Handle string timestamp (from new format)
                if isinstance(timestamp, str):
                    if 'UTC' in timestamp:
                        # Parse "1995-11-18 02:01:30 UTC" format
                        from datetime import datetime
                        dt = datetime.strptime(timestamp.replace(' UTC', ''), '%Y-%m-%d %H:%M:%S')
                        return dt.year
                    else:
                        # Try to convert string to numeric timestamp
                        timestamp = int(timestamp)
                
                # Handle numeric timestamp (from original format - the working output.json)
                if isinstance(timestamp, (int, float)):
                    return datetime.fromtimestamp(timestamp / 1000).year
                    
            except (ValueError, OSError, TypeError):
                pass
        
        return None
    
    def _parse_article_date(self, item: Dict[str, Any]) -> Optional[datetime]:
        """Parse article date from item"""
        if item.get('lastmod'):
            try:
                timestamp = item['lastmod']
                if isinstance(timestamp, str):
                    timestamp = int(timestamp)
                return datetime.fromtimestamp(timestamp / 1000)
            except (ValueError, OSError):
                pass
        return None
    
    def scrape_articles(self, articles: List[Dict[str, Any]], checkpoint_file: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Scrape multiple articles using thread pool
        
        Args:
            articles: List of article information dictionaries
            checkpoint_file: Optional checkpoint file path
            
        Returns:
            List of scraping results
        """
        if not articles:
            logger.warning("No articles to process")
            return []
        
        logger.info(f"Starting article scraping: {len(articles)} articles with {self.max_workers} workers")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_article = {
                executor.submit(self.process_single_article, article): article 
                for article in articles
            }
            
            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_article), 1):
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Save checkpoint periodically
                    if checkpoint_file and i % CHECKPOINT_FREQUENCY == 0:
                        self.file_handler.save_checkpoint(results, checkpoint_file)
                        successful = len([r for r in results if r['success']])
                        logger.info(f"Progress: {i}/{len(articles)}, Success: {successful}, Rate: {successful/i*100:.1f}%")
                    
                    # Respectful delay
                    time.sleep(DEFAULT_DELAY_BETWEEN_REQUESTS)
                    
                except Exception as e:
                    article = future_to_article[future]
                    logger.error(f"Task failed for {article['url']}: {e}")
                    # Add error result
                    results.append(self._create_failed_result(article, 'Task execution failed', str(e)))
        
        # Final statistics
        successful = len([r for r in results if r['success']])
        failed = len(results) - successful
        total_chars = sum(r.get('text_length', 0) for r in results if r['success'])
        
        logger.info("Article scraping completed")
        logger.info(f"Results: {successful} successful, {failed} failed")
        logger.info(f"Success rate: {successful/len(results)*100:.1f}%")
        logger.info(f"Total text captured: {total_chars:,} characters")
        
        if successful > 0:
            avg_chars = total_chars // successful
            logger.info(f"Average per article: {avg_chars} characters")
        
        return results
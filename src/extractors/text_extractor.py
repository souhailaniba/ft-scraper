"""
Text extraction utilities using newspaper4k
"""

from newspaper import Article
from typing import Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TextExtractor:
    """Text extractor using newspaper4k for article content extraction"""
    
    def __init__(self):
        """Initialize text extractor"""
        logger.info("Text extractor initialized with newspaper4k")
    
    def extract_from_html(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extract article text and metadata from HTML content
        
        Args:
            html_content: Raw HTML content
            url: Article URL
            
        Returns:
            Dictionary with extracted data
        """
        try:
            # Create Article instance
            article = Article(url)
            
            # Set HTML content (compatible with newspaper4k v0.9.3.1)
            article.html = html_content
            
            # Parse the article
            article.parse()
            
            # Extract summary if available
            summary = self._extract_summary(article)
            
            # Build result dictionary
            result = {
                'title': article.title or 'No title found',
                'text': article.text or 'No text extracted',
                'authors': list(article.authors) if article.authors else [],
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'top_image': article.top_image or None,
                'summary': summary,
                'text_length': len(article.text) if article.text else 0,
                'extraction_success': bool(article.text and len(article.text) > 50)
            }
            
            if result['extraction_success']:
                logger.debug(f"Successfully extracted {result['text_length']} characters from {url}")
            else:
                logger.warning(f"Low quality extraction from {url}: {result['text_length']} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"Text extraction failed for {url}: {e}")
            # Return a basic fallback result (like original logic)
            return {
                'title': 'Extraction failed',
                'text': f'Failed to extract text: {str(e)}',
                'authors': [],
                'publish_date': None,
                'top_image': None,
                'summary': None,
                'text_length': 0,
                'extraction_success': False,
                'error': str(e)
            }
    
    def _extract_summary(self, article: Article) -> Optional[str]:
        """
        Extract article summary using NLP
        
        Args:
            article: Newspaper Article instance
            
        Returns:
            Summary text or None
        """
        try:
            if hasattr(article, 'summary'):
                article.nlp()
                return article.summary
        except Exception as e:
            logger.debug(f"Summary extraction failed: {e}")
        return None
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create error result dictionary
        
        Args:
            error_message: Error description
            
        Returns:
            Error result dictionary
        """
        return {
            'title': 'Extraction failed',
            'text': f'Failed to extract text: {error_message}',
            'authors': [],
            'publish_date': None,
            'top_image': None,
            'summary': None,
            'text_length': 0,
            'extraction_success': False,
            'error': error_message
        }
    
    def validate_extraction(self, extracted_data: Dict[str, Any]) -> bool:
        """
        Validate extraction quality
        
        Args:
            extracted_data: Extracted data dictionary
            
        Returns:
            True if extraction meets quality criteria
        """
        # Check if extraction was successful
        if not extracted_data.get('extraction_success', False):
            return False
        
        # Check minimum text length
        text_length = extracted_data.get('text_length', 0)
        if text_length < 100:
            logger.warning(f"Low quality extraction: only {text_length} characters")
            return False
        
        # Check for meaningful title
        title = extracted_data.get('title', '')
        if not title or title == 'No title found' or len(title) < 10:
            logger.warning("Poor quality title extraction")
            return False
        
        return True
    
    def extract_batch(self, html_articles: list) -> list:
        """
        Extract text from multiple HTML articles
        
        Args:
            html_articles: List of tuples (html_content, url)
            
        Returns:
            List of extraction results
        """
        results = []
        
        for html_content, url in html_articles:
            result = self.extract_from_html(html_content, url)
            results.append(result)
        
        successful = len([r for r in results if r.get('extraction_success', False)])
        logger.info(f"Batch extraction complete: {successful}/{len(results)} successful")
        
        return results
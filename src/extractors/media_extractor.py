"""
Media extraction utilities for FT articles
"""

import re
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .logger import get_logger

logger = get_logger(__name__)


class MediaExtractor:
    """Extract media links and content from FT articles"""
    
    def __init__(self):
        """Initialize media extractor with common patterns"""
        self.image_patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
            r'<figure[^>]*>.*?<img[^>]+src=["\']([^"\']+)["\'].*?</figure>',
            r'data-src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp))["\']',
        ]
        
        self.video_patterns = [
            r'<video[^>]+src=["\']([^"\']+)["\'][^>]*>',
            r'<source[^>]+src=["\']([^"\']+\.(?:mp4|webm|ogg))["\']',
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'youtu\.be/([a-zA-Z0-9_-]+)',
            r'vimeo\.com/(\d+)',
        ]
        
        self.ft_specific_patterns = [
            r'prod-upp-image-read\.ft\.com/[^"\']+',
            r'ft\.com/fastft/files/[^"\']+',
            r'ft\.com/ig-template/[^"\']+',
        ]
    
    def extract_from_html(self, html_content: str, base_url: str = "https://www.ft.com") -> Dict[str, Any]:
        """Extract comprehensive media from HTML content"""
        if not html_content:
            return self._empty_media_result()
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            result = {
                'images': self._extract_images(soup, base_url),
                'videos': self._extract_videos(soup, base_url),
                'galleries': self._extract_galleries(soup),
                'infographics': self._extract_infographics(soup, base_url),
                'social_media': self._extract_social_media(soup),
                'audio': self._extract_audio(soup, base_url),
                'charts': self._extract_charts(soup, base_url)
            }
            
            # Add summary statistics
            result['summary'] = {
                'total_images': len(result['images']),
                'total_videos': len(result['videos']),
                'total_galleries': len(result['galleries']),
                'total_infographics': len(result['infographics']),
                'total_social_media': len(result['social_media']),
                'total_audio': len(result['audio']),
                'total_charts': len(result['charts'])
            }
            
            logger.debug(f"Extracted media: {result['summary']}")
            return result
            
        except Exception as e:
            logger.error(f"Media extraction failed: {e}")
            return self._empty_media_result()
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract images from HTML"""
        images = []
        
        # Find all img tags
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if not src:
                continue
            
            # Make URL absolute
            full_url = urljoin(base_url, src)
            
            image_info = {
                'url': full_url,
                'alt': img.get('alt', '').strip(),
                'caption': self._get_image_caption(img),
                'width': self._safe_int(img.get('width')),
                'height': self._safe_int(img.get('height')),
                'class': ' '.join(img.get('class', [])),
                'is_ft_image': 'ft.com' in full_url or 'prod-upp-image' in full_url
            }
            
            images.append(image_info)
        
        # Find FT-specific image patterns
        for pattern in self.ft_specific_patterns:
            matches = re.finditer(pattern, str(soup), re.IGNORECASE)
            for match in matches:
                url = match.group(0)
                if not url.startswith('http'):
                    url = 'https://' + url
                
                images.append({
                    'url': url,
                    'alt': '',
                    'caption': '',
                    'width': None,
                    'height': None,
                    'class': 'ft-specific',
                    'is_ft_image': True
                })
        
        # Remove duplicates
        seen_urls = set()
        unique_images = []
        for img in images:
            if img['url'] not in seen_urls:
                seen_urls.add(img['url'])
                unique_images.append(img)
        
        return unique_images
    
    def _extract_videos(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract videos from HTML"""
        videos = []
        
        # Video tags
        for video in soup.find_all('video'):
            src = video.get('src')
            if src:
                videos.append({
                    'url': urljoin(base_url, src),
                    'type': 'video',
                    'platform': 'native',
                    'title': video.get('title', ''),
                    'poster': video.get('poster', ''),
                    'duration': video.get('duration', ''),
                    'controls': video.has_attr('controls')
                })
        
        # Source tags within video
        for source in soup.find_all('source'):
            parent = source.parent
            if parent and parent.name == 'video':
                src = source.get('src')
                if src:
                    videos.append({
                        'url': urljoin(base_url, src),
                        'type': source.get('type', 'video'),
                        'platform': 'native',
                        'title': parent.get('title', ''),
                        'poster': parent.get('poster', ''),
                        'duration': parent.get('duration', ''),
                        'controls': parent.has_attr('controls')
                    })
        
        # YouTube embeds
        youtube_pattern = r'(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([a-zA-Z0-9_-]+)'
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            match = re.search(youtube_pattern, src)
            if match:
                video_id = match.group(1)
                videos.append({
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'type': 'video',
                    'platform': 'youtube',
                    'video_id': video_id,
                    'title': iframe.get('title', ''),
                    'embed_url': src
                })
        
        # Vimeo embeds
        vimeo_pattern = r'vimeo\.com/(?:video/)?(\d+)'
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            match = re.search(vimeo_pattern, src)
            if match:
                video_id = match.group(1)
                videos.append({
                    'url': f'https://vimeo.com/{video_id}',
                    'type': 'video',
                    'platform': 'vimeo',
                    'video_id': video_id,
                    'title': iframe.get('title', ''),
                    'embed_url': src
                })
        
        return videos
    
    def _extract_galleries(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract image galleries"""
        galleries = []
        
        # Look for common gallery patterns
        gallery_selectors = [
            '.gallery',
            '.slideshow', 
            '.image-gallery',
            '.ft-slideshow',
            '[data-gallery]'
        ]
        
        for selector in gallery_selectors:
            for gallery in soup.select(selector):
                images_in_gallery = gallery.find_all('img')
                if len(images_in_gallery) > 1:  # Only consider as gallery if multiple images
                    galleries.append({
                        'type': 'gallery',
                        'title': self._get_element_text(gallery.find(['h2', 'h3', '.title'])),
                        'image_count': len(images_in_gallery),
                        'images': [img.get('src') or img.get('data-src') for img in images_in_gallery if img.get('src') or img.get('data-src')]
                    })
        
        return galleries
    
    def _extract_infographics(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract infographics and interactive content"""
        infographics = []
        
        # Look for FT's interactive content
        interactive_selectors = [
            '.ft-interactive',
            '.infographic',
            '.data-viz',
            '[data-component="interactive"]',
            '.ig-container'
        ]
        
        for selector in interactive_selectors:
            for element in soup.select(selector):
                infographics.append({
                    'type': 'infographic',
                    'title': self._get_element_text(element.find(['h2', 'h3', '.title'])),
                    'url': element.get('data-url') or element.get('src'),
                    'class': ' '.join(element.get('class', [])),
                    'interactive': True
                })
        
        # Look for chart/graph images
        for img in soup.find_all('img'):
            alt = img.get('alt', '').lower()
            src = img.get('src', '')
            if any(keyword in alt for keyword in ['chart', 'graph', 'infographic', 'visualization']):
                infographics.append({
                    'type': 'chart_image',
                    'title': img.get('alt', ''),
                    'url': urljoin(base_url, src),
                    'interactive': False
                })
        
        return infographics
    
    def _extract_social_media(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract embedded social media content"""
        social_media = []
        
        # Twitter/X embeds
        for blockquote in soup.find_all('blockquote', class_=lambda x: x and 'twitter' in ' '.join(x)):
            social_media.append({
                'platform': 'twitter',
                'type': 'embed',
                'url': blockquote.get('cite', ''),
                'content': self._get_element_text(blockquote)
            })
        
        # Instagram embeds
        for blockquote in soup.find_all('blockquote', class_=lambda x: x and 'instagram' in ' '.join(x)):
            social_media.append({
                'platform': 'instagram',
                'type': 'embed',
                'url': blockquote.get('cite', ''),
                'content': self._get_element_text(blockquote)
            })
        
        return social_media
    
    def _extract_audio(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract audio content"""
        audio = []
        
        # Audio tags
        for audio_tag in soup.find_all('audio'):
            src = audio_tag.get('src')
            if src:
                audio.append({
                    'url': urljoin(base_url, src),
                    'type': 'audio',
                    'title': audio_tag.get('title', ''),
                    'controls': audio_tag.has_attr('controls'),
                    'duration': audio_tag.get('duration', '')
                })
        
        # Look for podcast/audio references
        for link in soup.find_all('a'):
            href = link.get('href', '')
            text = link.get_text().lower()
            if any(keyword in text for keyword in ['podcast', 'audio', 'listen']):
                if any(ext in href for ext in ['.mp3', '.wav', '.ogg']):
                    audio.append({
                        'url': urljoin(base_url, href),
                        'type': 'podcast',
                        'title': link.get_text().strip(),
                        'controls': True,
                        'duration': ''
                    })
        
        return audio
    
    def _extract_charts(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract financial charts and data visualizations"""
        charts = []
        
        # Look for FT's chart containers
        chart_selectors = [
            '.chart-container',
            '.ft-chart',
            '.data-chart',
            '[data-chart]',
            '.highcharts-container'
        ]
        
        for selector in chart_selectors:
            for chart in soup.select(selector):
                charts.append({
                    'type': 'chart',
                    'title': self._get_element_text(chart.find(['h3', 'h4', '.chart-title'])),
                    'data_source': chart.get('data-source', ''),
                    'chart_type': chart.get('data-chart-type', 'unknown'),
                    'interactive': 'highcharts' in chart.get('class', [])
                })
        
        return charts
    
    def _get_image_caption(self, img_tag) -> str:
        """Extract caption for an image"""
        # Look in parent figure
        figure = img_tag.find_parent('figure')
        if figure:
            caption = figure.find('figcaption')
            if caption:
                return self._get_element_text(caption)
        
        # Look for nearby caption div
        parent = img_tag.parent
        if parent:
            caption_div = parent.find_next_sibling(['div', 'p'], class_=lambda x: x and 'caption' in ' '.join(x))
            if caption_div:
                return self._get_element_text(caption_div)
        
        return ''
    
    def _get_element_text(self, element) -> str:
        """Safely extract text from element"""
        if element:
            return element.get_text().strip()
        return ''
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int"""
        if value:
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
        return None
    
    def _empty_media_result(self) -> Dict[str, Any]:
        """Return empty media result structure"""
        return {
            'images': [],
            'videos': [],
            'galleries': [],
            'infographics': [],
            'social_media': [],
            'audio': [],
            'charts': [],
            'summary': {
                'total_images': 0,
                'total_videos': 0,
                'total_galleries': 0,
                'total_infographics': 0,
                'total_social_media': 0,
                'total_audio': 0,
                'total_charts': 0
            }
        }
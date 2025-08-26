"""
Sitemap scraper for FT.com
"""

from concurrent import futures
from gzip import BadGzipFile, GzipFile
from urllib.request import Request, urlopen
from xml.etree import ElementTree
import pandas as pd
from typing import List, Dict, Any, Optional

from config.settings import FT_SITEMAP_URL, FT_USER_AGENT, DEFAULT_MAX_WORKERS
from src.utils.logger import get_logger
from src.utils.file_handler import FileHandler

logger = get_logger(__name__, 'sitemap_scraper.log')


class SitemapScraper:
    """Sitemap scraper for discovering and parsing FT.com article URLs"""
    
    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS):
        """
        Initialize sitemap scraper
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        self.headers = {
            "User-Agent": FT_USER_AGENT,
            "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.ft.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
        }
        logger.info("Sitemap scraper initialized")
    
    def _get_sitemaps_from_robots(self, robots_url: str) -> List[str]:
        """Extract sitemap URLs from robots.txt"""
        sitemaps = []
        try:
            robots_page = urlopen(Request(robots_url, headers=self.headers), timeout=30)
            for line in robots_page.readlines():
                line_split = [s.strip() for s in line.decode().split(":", maxsplit=1)]
                if line_split[0].lower() == "sitemap":
                    sitemaps.append(line_split[1])
            logger.info(f"Found {len(sitemaps)} sitemaps in robots.txt")
        except Exception as e:
            logger.error(f"Failed to parse robots.txt: {e}")
        return sitemaps
    
    def _parse_sitemap_xml(self, root: ElementTree.Element) -> pd.DataFrame:
        """Parse sitemap XML into DataFrame"""
        data = {}
        
        # Initialize data structure
        for node in root:
            for n in node:
                if "loc" in n.tag:
                    data[n.text] = {}
        
        def parse_xml_node(node, node_url, prefix=""):
            """Recursively parse XML node"""
            keys = []
            for element in node:
                if element.text:
                    tag = element.tag.split("}")[-1]
                    data[node_url][prefix + tag] = element.text
                    keys.append(tag)
                    prefix = prefix if tag in keys else ""
                if list(element):
                    parse_xml_node(
                        element, node_url, prefix=element.tag.split("}")[-1] + "_"
                    )
        
        # Parse all nodes
        for node in root:
            node_url = [n.text for n in node if "loc" in n.tag][0]
            parse_xml_node(node, node_url=node_url)
        
        return pd.DataFrame(data.values())
    
    def _fetch_sitemap_content(self, sitemap_url: str) -> Optional[str]:
        """Fetch sitemap content from URL"""
        try:
            if sitemap_url.endswith("xml.gz"):
                # Handle gzipped XML
                self.headers["accept-encoding"] = "gzip"
                xml_resp = urlopen(Request(sitemap_url, headers=self.headers), timeout=30)
                xml_gz = GzipFile(fileobj=xml_resp)
                try:
                    xml_content = xml_gz.read()
                except BadGzipFile:
                    logger.warning(f"{sitemap_url} is not valid gzip. Falling back to plain XML")
                    xml_resp = urlopen(Request(sitemap_url, headers=self.headers), timeout=30)
                    xml_content = xml_resp.read()
            else:
                # Handle plain XML
                xml_resp = urlopen(Request(sitemap_url, headers=self.headers), timeout=30)
                xml_content = xml_resp.read()
            
            return xml_content
            
        except Exception as e:
            logger.error(f"Failed to fetch sitemap {sitemap_url}: {e}")
            return None
    
    def scrape_sitemap(self, sitemap_url: str = FT_SITEMAP_URL, recursive: bool = True) -> pd.DataFrame:
        """
        Scrape sitemap and return DataFrame
        
        Args:
            sitemap_url: URL to sitemap or robots.txt
            recursive: Whether to recursively parse sitemap indexes
            
        Returns:
            DataFrame with sitemap data
        """
        logger.info(f"Starting sitemap scrape: {sitemap_url}")
        
        # Handle robots.txt
        if sitemap_url.endswith("robots.txt"):
            sitemaps = self._get_sitemaps_from_robots(sitemap_url)
            if not sitemaps:
                logger.error("No sitemaps found in robots.txt")
                return pd.DataFrame()
            
            # Process all sitemaps
            all_data = []
            for sitemap in sitemaps:
                sitemap_data = self.scrape_sitemap(sitemap, recursive=recursive)
                if not sitemap_data.empty:
                    all_data.append(sitemap_data)
            
            if all_data:
                return pd.concat(all_data, ignore_index=True)
            return pd.DataFrame()
        
        # Fetch sitemap content
        xml_content = self._fetch_sitemap_content(sitemap_url)
        if not xml_content:
            return pd.DataFrame()
        
        # Parse XML
        try:
            root = ElementTree.fromstring(xml_content)
        except Exception as e:
            logger.error(f"Failed to parse XML from {sitemap_url}: {e}")
            return pd.DataFrame()
        
        # Handle sitemap index
        if (root.tag.split("}")[-1] == "sitemapindex") and recursive:
            logger.info(f"Processing sitemap index: {sitemap_url}")
            return self._process_sitemap_index(root, sitemap_url)
        
        # Handle regular sitemap
        logger.info(f"Processing sitemap: {sitemap_url}")
        sitemap_df = self._parse_sitemap_xml(root)
        
        if not sitemap_df.empty:
            sitemap_df["sitemap"] = sitemap_url
            sitemap_df = self._enhance_dataframe(sitemap_df, xml_content)
        
        logger.info(f"Processed {len(sitemap_df)} entries from {sitemap_url}")
        return sitemap_df
    
    def _process_sitemap_index(self, root: ElementTree.Element, sitemap_url: str) -> pd.DataFrame:
        """Process sitemap index with multiple sitemaps"""
        sitemap_urls = []
        
        for elem in root:
            for el in elem:
                if "loc" in el.tag:
                    if el.text != sitemap_url:  # Avoid self-reference
                        sitemap_urls.append(el.text)
                    else:
                        logger.warning(f"Sitemap contains self-reference: {sitemap_url}")
        
        if not sitemap_urls:
            logger.warning("No valid sitemap URLs found in index")
            return pd.DataFrame()
        
        # Process sitemaps in parallel
        all_data = []
        with futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.scrape_sitemap, url): url 
                for url in sitemap_urls
            }
            
            for future in futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if not result.empty:
                        all_data.append(result)
                except Exception as e:
                    logger.error(f"Failed to process sitemap {url}: {e}")
                    # Add error entry
                    error_df = pd.DataFrame({
                        "sitemap": [url],
                        "errors": [str(e)]
                    })
                    all_data.append(error_df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    def _enhance_dataframe(self, df: pd.DataFrame, xml_content: bytes) -> pd.DataFrame:
        """Enhance DataFrame with additional metadata"""
        # Convert lastmod to datetime
        if "lastmod" in df.columns:
            try:
                df["lastmod"] = pd.to_datetime(df["lastmod"], utc=True)
            except Exception:
                pass
        
        # Convert priority to float
        if "priority" in df.columns:
            try:
                df["priority"] = df["priority"].astype(float)
            except Exception:
                pass
        
        # Add metadata
        df["sitemap_size_mb"] = len(xml_content) / 1024 / 1024
        df["download_date"] = pd.Timestamp.now(tz="UTC")
        
        return df
    
    def save_results(self, df: pd.DataFrame, filepath: str) -> bool:
        """
        Save scraping results to JSON file (matching original output.json format)
        
        Args:
            df: DataFrame to save
            filepath: Output file path
            
        Returns:
            Success status
        """
        try:
            # Convert DataFrame to JSON-serializable format
            # Keep the original format - numeric timestamps, not string conversion
            df_copy = df.copy()
            
            # Convert Timestamp columns to numeric (milliseconds) like original
            for col in df_copy.columns:
                if df_copy[col].dtype == 'datetime64[ns, UTC]':
                    # Convert to milliseconds timestamp (like original output.json)
                    df_copy[col] = (df_copy[col].astype('int64') // 1000000).astype('Int64')
                elif any(isinstance(val, pd.Timestamp) for val in df_copy[col].dropna().head(5)):
                    df_copy[col] = df_copy[col].apply(
                        lambda x: int(x.timestamp() * 1000) if isinstance(x, pd.Timestamp) else x
                    )
            
            # Convert download_date to numeric timestamp (like original)
            if 'download_date' in df_copy.columns:
                df_copy['download_date'] = df_copy['download_date'].apply(
                    lambda x: int(x.timestamp() * 1000) if isinstance(x, pd.Timestamp) else x
                )
            
            # Convert to records (same as original)
            data = df_copy.to_dict('records')
            
            # Save using FileHandler with original format
            file_handler = FileHandler()
            success = file_handler.save_json(data, Path(filepath))
            
            if success:
                logger.info(f"Saved {len(data)} sitemap entries to {filepath}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return False
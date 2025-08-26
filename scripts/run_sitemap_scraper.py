#!/usr/bin/env python3
"""
Script to run FT sitemap scraper
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import FT_SITEMAP_URL, SITEMAP_OUTPUT_FILE, DEFAULT_MAX_WORKERS
from src.scrapers.sitemap_scraper import SitemapScraper
from src.utils.logger import get_logger
from src.utils.file_handler import FileHandler

logger = get_logger(__name__)


def main():
    """Main function to run sitemap scraper"""
    
    # Check for test mode
    test_mode = '--test' in sys.argv or '-t' in sys.argv
    
    print("=" * 60)
    print(f"FT Sitemap Scraper {'(TEST MODE)' if test_mode else ''}")
    print("=" * 60)
    print(f"Target URL: {FT_SITEMAP_URL}")
    print(f"Max Workers: {DEFAULT_MAX_WORKERS}")
    print(f"Output File: {SITEMAP_OUTPUT_FILE}")
    if test_mode:
        print("Mode: TEST - Will process only first few sitemaps")
    print("=" * 60)
    
    try:
        # Initialize scraper
        scraper = SitemapScraper(max_workers=DEFAULT_MAX_WORKERS)
        
        if test_mode:
            # Test mode - just process a few sitemaps for validation
            logger.info("Running in TEST MODE - processing limited sitemaps...")
            
            # Get sitemap index first
            test_df = scraper.scrape_sitemap(FT_SITEMAP_URL, recursive=False)
            
            if test_df.empty:
                logger.error("Failed to get sitemap index")
                return False
            
            # Process just first 3-5 individual sitemaps
            test_sitemaps = []
            for _, row in test_df.head(5).iterrows():
                if row.get('loc') and 'archive' not in str(row.get('loc')):  # Skip large archives
                    test_sitemaps.append(row['loc'])
                if len(test_sitemaps) >= 3:  # Limit to 3 for quick test
                    break
            
            if not test_sitemaps:
                logger.warning("No suitable test sitemaps found, using first 2 from index")
                test_sitemaps = [row['loc'] for _, row in test_df.head(2).iterrows() if row.get('loc')]
            
            logger.info(f"Testing with {len(test_sitemaps)} sitemaps:")
            for sitemap in test_sitemaps:
                logger.info(f"  - {sitemap}")
            
            # Process test sitemaps
            all_data = []
            for sitemap_url in test_sitemaps:
                logger.info(f"Processing test sitemap: {sitemap_url}")
                sitemap_df = scraper.scrape_sitemap(sitemap_url, recursive=False)
                if not sitemap_df.empty:
                    all_data.append(sitemap_df)
            
            if all_data:
                import pandas as pd
                df = pd.concat(all_data, ignore_index=True)
            else:
                df = pd.DataFrame()
        
        else:
            # Full mode - process everything
            logger.info("Starting FULL sitemap scraping process...")
            df = scraper.scrape_sitemap(FT_SITEMAP_URL, recursive=True)
        
        if df.empty:
            logger.error("No data scraped from sitemap")
            return False
        
        # Save results
        logger.info(f"Scraping completed. Found {len(df)} entries.")
        
        # Convert to JSON format and save
        data = df.to_dict('records')
        file_handler = FileHandler()
        
        # Use different filename for test mode
        output_file = SITEMAP_OUTPUT_FILE
        if test_mode:
            output_file = output_file.parent / f"sitemap_data_test.json"
        
        success = file_handler.save_json(data, output_file)
        
        if success:
            # Print statistics
            valid_articles = len([item for item in data if item.get('loc') and not item.get('errors')])
            error_count = len([item for item in data if item.get('errors')])
            
            print(f"\n{'Test ' if test_mode else ''}Scraping Results:")
            print(f"Total entries: {len(data)}")
            print(f"Valid articles: {valid_articles}")
            print(f"Errors: {error_count}")
            print(f"Success rate: {valid_articles/len(data)*100:.1f}%" if len(data) > 0 else "N/A")
            print(f"\nData saved to: {output_file}")
            
            # Show sample URLs
            sample_urls = [item['loc'] for item in data[:5] if item.get('loc')]
            if sample_urls:
                print("\nSample URLs discovered:")
                for i, url in enumerate(sample_urls, 1):
                    print(f"  {i}. {url}")
            
            if test_mode:
                print(f"\n✅ TEST MODE completed successfully!")
                print(f"📊 Processed {len(data)} entries from limited sitemaps")
                print(f"🔄 To run full scraping, use: python run_sitemap_scraper.py")
            
            return True
        else:
            logger.error("Failed to save results")
            return False
            
    except KeyboardInterrupt:
        print(f"\n{'Test ' if test_mode else ''}Scraping interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("FT Sitemap Scraper")
        print("Usage:")
        print("  python run_sitemap_scraper.py          # Full scraping")
        print("  python run_sitemap_scraper.py --test   # Test mode (limited)")
        print("  python run_sitemap_scraper.py -t       # Test mode (short)")
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)
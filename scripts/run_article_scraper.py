#!/usr/bin/env python3
"""
Script to run FT article scraper
"""

import sys
import os
from pathlib import Path
import argparse

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import (
    SITEMAP_OUTPUT_FILE, SCRAPED_ARTICLES_FILE, MIN_ARTICLE_YEAR, 
    DEFAULT_MAX_WORKERS, DEFAULT_ARTICLE_LIMIT
)
from src.scrapers.article_scraper import ArticleScraper
from src.utils.logger import get_logger
from src.utils.file_handler import FileHandler

logger = get_logger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='FT Article Scraper')
    parser.add_argument('--test', '-t', action='store_true', 
                       help='Test mode (process only 5 articles)')
    parser.add_argument('--limit', '-l', type=int, 
                       help='Limit number of articles to scrape (e.g., --limit 20)')
    parser.add_argument('--workers', '-w', type=int, default=DEFAULT_MAX_WORKERS,
                       help=f'Number of worker threads (default: {DEFAULT_MAX_WORKERS})')
    parser.add_argument('--year', '-y', type=int, default=MIN_ARTICLE_YEAR,
                       help=f'Minimum article year (default: {MIN_ARTICLE_YEAR})')
    parser.add_argument('--input', '-i', type=str,
                       help='Input sitemap file (default: auto-detect)')
    parser.add_argument('--no-confirm', action='store_true',
                       help='Skip confirmation prompt')
    return parser.parse_args()


def find_sitemap_file():
    """Find the best available sitemap file"""
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Look for sitemap files in order of preference
    candidates = [
        # Recent generated files (small, clean)
        'raw/sitemap_data_limit_500.json',
        'raw/sitemap_data_limit_1000.json', 
        'raw/sitemap_data_limit_300.json',
        'raw/sitemap_data_limit_200.json',
        'raw/sitemap_data_limit_100.json',
        # Main sitemap file (now should be clean)
        'raw/sitemap_data.json',
        # Working backup files
        'processed/output.json',
        'raw/sitemap_data_working.json',
        # Test files (last resort)
        'raw/sitemap_data_test.json'
    ]
    
    for candidate in candidates:
        filepath = data_dir / candidate
        if filepath.exists():
            return filepath
    
    return SITEMAP_OUTPUT_FILE


def main():
    """Main function to run article scraper"""
    
    args = parse_arguments()
    test_mode = args.test
    limit = args.limit or (5 if test_mode else DEFAULT_ARTICLE_LIMIT)
    max_workers = args.workers if not test_mode else 2  # Reduce workers in test mode
    min_year = args.year if args.year != MIN_ARTICLE_YEAR else (2025 if test_mode else MIN_ARTICLE_YEAR)
    no_confirm = args.no_confirm or test_mode  # Skip confirmation in test mode
    
    # Determine input file
    if args.input:
        input_file = Path(args.input)
    else:
        input_file = find_sitemap_file()
    
    print("=" * 60)
    print(f"FT Article Scraper{' (TEST MODE)' if test_mode else ''}")
    print("=" * 60)
    print(f"Sitemap Data: {input_file}")
    print(f"Min Year: {min_year}{' (2025+ for latest articles)' if test_mode and min_year == 2025 else ''}")
    print(f"Max Workers: {max_workers}")
    print(f"Limit: {limit or 'No limit'}")
    if test_mode:
        print("Mode: TEST - Quick validation with latest articles")
    print(f"Output File: {SCRAPED_ARTICLES_FILE}")
    print("=" * 60)
    
    try:
        # Initialize scraper
        scraper = ArticleScraper(max_workers=max_workers)
        
        # Check API health
        if not scraper.check_api_health():
            print("\nERROR: Node.js API is not running or not ready!")
            print("Please start the API server first:")
            print("  cd ft_scraper/server")
            print("  node server.js")
            return False
        
        # Load article URLs
        logger.info("Loading article URLs from sitemap data...")
        articles = scraper.load_article_urls(
            filepath=input_file,
            min_year=min_year,
            limit=limit
        )
        
        if not articles:
            logger.error("No articles found to process")
            if min_year > 2020:
                print(f"\nTIP: Try with older articles: --year 2015")
            elif input_file.name.endswith('_test.json'):
                print(f"\nTIP: Test file may only have old articles. Try: --year 1990")
            else:
                print(f"\nTIP: Generate fresh sitemap data: python run_sitemap_scraper.py --limit 500")
            return False
        
        print(f"\nLoaded {len(articles)} articles for processing")
        
        # Show year distribution
        year_counts = {}
        for article in articles:
            year = article.get('year', 'Unknown')
            year_counts[year] = year_counts.get(year, 0) + 1
        
        print("Year distribution:")
        for year in sorted(year_counts.keys(), reverse=True):
            print(f"  {year}: {year_counts[year]} articles")
        
        # Sample URLs
        if articles:
            print("\nSample URLs to be processed:")
            for i, article in enumerate(articles[:3], 1):
                date_str = f" ({article['year']})" if article.get('year') else ""
                print(f"  {i}. {article['url']}{date_str}")
        
        # Confirm processing (unless --no-confirm or test mode)
        if not no_confirm:
            response = input(f"\nProceed with scraping {len(articles)} articles? (y/N): ").lower().strip()
            if response != 'y':
                print("Scraping cancelled.")
                return False
        elif test_mode:
            print(f"\nTEST MODE: Auto-proceeding with {len(articles)} articles...")
        
        # Run scraping
        logger.info(f"Starting article scraping process{' (TEST MODE)' if test_mode else ''}...")
        
        # Use different checkpoint file for test/limited runs
        if test_mode:
            checkpoint_file = SCRAPED_ARTICLES_FILE.parent / "checkpoint_test.json"
        elif limit:
            checkpoint_file = SCRAPED_ARTICLES_FILE.parent / f"checkpoint_limit_{limit}.json"
        else:
            checkpoint_file = SCRAPED_ARTICLES_FILE.parent / "checkpoint_articles.json"
        
        results = scraper.scrape_articles(articles, checkpoint_file)
        
        if not results:
            logger.error("No results from scraping")
            return False
        
        # Use different output file for test/limited runs
        if test_mode:
            output_file = SCRAPED_ARTICLES_FILE.parent / "scraped_articles_test.json"
        elif limit:
            output_file = SCRAPED_ARTICLES_FILE.parent / f"scraped_articles_limit_{limit}.json"
        else:
            output_file = SCRAPED_ARTICLES_FILE
        
        # Save final results
        file_handler = FileHandler()
        success = file_handler.save_json(results, output_file)
        
        if success:
            # Print final statistics
            stats = file_handler.analyze_json_data(results)
            
            mode_text = "Test " if test_mode else f"Limited ({limit}) " if limit else ""
            print(f"\n{mode_text}Scraping Results:")
            print(f"Total processed: {stats['total_count']}")
            print(f"Successful: {stats['successful']}")
            print(f"Failed: {stats['failed']}")
            print(f"Success rate: {stats['success_rate']}%")
            print(f"Total text captured: {stats['total_characters']:,} characters")
            print(f"Average per article: {stats['average_chars_per_article']} characters")
            print(f"\nResults saved to: {output_file}")
            
            if test_mode:
                print(f"\nTEST MODE completed successfully!")
                print(f"Validated {stats['successful']} articles with {stats['success_rate']}% success rate")
            elif limit:
                print(f"\nLIMITED MODE completed successfully!")
                print(f"Processed {stats['total_count']} articles as requested")
            
            print(f"\nUsage examples:")
            print(f"   python run_article_scraper.py --test          # Test mode (5 articles)")
            print(f"   python run_article_scraper.py --limit 20      # Limit to 20 articles")
            print(f"   python run_article_scraper.py --year 2020     # Only 2020+ articles")
            print(f"   python run_article_scraper.py                 # Full scraping")
            
            return True
        else:
            logger.error("Failed to save results")
            return False
            
    except KeyboardInterrupt:
        mode_text = "Test " if test_mode else f"Limited ({limit}) " if limit else ""
        print(f"\n{mode_text}Scraping interrupted by user")
        print("Partial results may be available in checkpoint file")
        return False
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
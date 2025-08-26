#!/usr/bin/env python3
"""
Demo Pipeline for FT Scraper - August 2025 Focus
Demonstrates complete workflow with minimal resources
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DEFAULT_MAX_WORKERS
from src.scrapers.sitemap_scraper import SitemapScraper
from src.scrapers.article_scraper import ArticleScraper
from src.utils.logger import get_logger
from src.utils.file_handler import FileHandler

logger = get_logger(__name__, 'demo_pipeline.log')


class FTDemoPipeline:
    """Demo pipeline for FT scraping - August 2025 focus"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.demo_dir = self.data_dir / 'demo'
        self.demo_dir.mkdir(parents=True, exist_ok=True)
        
        # Demo configuration
        self.demo_config = {
            'target_sitemaps': [
                'https://www.ft.com/sitemaps/archive-2025-8.xml',  # August 2025
                'https://www.ft.com/sitemaps/news.xml',            # Latest news
                'https://www.ft.com/sitemaps/opinion.xml',         # Opinion pieces
            ],
            'max_articles': 100,
            'min_year': 2025,
            'workers': 3
        }
        
        logger.info("Demo pipeline initialized")
    
    def step_1_discover_articles(self):
        """Step 1: Discover August 2025 articles from specific sitemaps"""
        
        print("🔍 STEP 1: Discovering August 2025 Articles")
        print("=" * 50)
        
        scraper = SitemapScraper(max_workers=2)
        all_data = []
        
        for i, sitemap_url in enumerate(self.demo_config['target_sitemaps'], 1):
            print(f"Processing sitemap {i}/{len(self.demo_config['target_sitemaps'])}: {sitemap_url.split('/')[-1]}")
            
            try:
                # Scrape individual sitemap (no recursion)
                df = scraper.scrape_sitemap(sitemap_url, recursive=False)
                
                if not df.empty:
                    data = df.to_dict('records')
                    all_data.extend(data)
                    print(f"  ✅ Found {len(data)} entries")
                else:
                    print(f"  ⚠️  No entries found")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                logger.error(f"Failed to process {sitemap_url}: {e}")
        
        if not all_data:
            print("❌ No articles discovered")
            return False
        
        # Save demo sitemap data
        demo_sitemap_file = self.demo_dir / 'demo_sitemap_august2025.json'
        file_handler = FileHandler()
        success = file_handler.save_json(all_data, demo_sitemap_file)
        
        if success:
            print(f"\n✅ Step 1 Complete!")
            print(f"📊 Discovered {len(all_data)} total entries")
            print(f"💾 Saved to: {demo_sitemap_file.name}")
            
            # Show sample URLs
            valid_articles = [item for item in all_data if item.get('loc') and not item.get('errors')]
            if valid_articles:
                print(f"📄 Valid articles: {len(valid_articles)}")
                print("Sample URLs:")
                for i, article in enumerate(valid_articles[:3], 1):
                    print(f"  {i}. {article['loc']}")
            
            return demo_sitemap_file
        else:
            print("❌ Failed to save sitemap data")
            return False
    
    def step_2_scrape_articles(self, sitemap_file):
        """Step 2: Scrape the 100 most recent articles"""
        
        print(f"\n📰 STEP 2: Scraping 100 Most Recent Articles")
        print("=" * 50)
        
        # Initialize article scraper
        scraper = ArticleScraper(max_workers=self.demo_config['workers'])
        
        # Check API health
        if not scraper.check_api_health():
            print("❌ Node.js API is not running!")
            print("Please start: cd ft_scraper/server && node server.js")
            return False
        
        print("✅ API health check passed")
        
        # Load articles
        articles = scraper.load_article_urls(
            filepath=sitemap_file,
            min_year=self.demo_config['min_year'],
            limit=self.demo_config['max_articles']
        )
        
        if not articles:
            print("❌ No articles found for scraping")
            return False
        
        print(f"📄 Loaded {len(articles)} articles for processing")
        
        # Show distribution
        year_counts = {}
        for article in articles:
            year = article.get('year', 'Unknown')
            year_counts[year] = year_counts.get(year, 0) + 1
        
        print("Year distribution:")
        for year in sorted(year_counts.keys(), reverse=True):
            print(f"  {year}: {year_counts[year]} articles")
        
        # Process articles
        print(f"\n🚀 Processing {len(articles)} articles...")
        
        demo_checkpoint = self.demo_dir / 'demo_checkpoint.json'
        results = scraper.scrape_articles(articles, demo_checkpoint)
        
        if not results:
            print("❌ No scraping results")
            return False
        
        # Save results
        demo_results_file = self.demo_dir / 'demo_scraped_articles_august2025.json'
        file_handler = FileHandler()
        success = file_handler.save_json(results, demo_results_file)
        
        if success:
            # Calculate statistics
            stats = file_handler.analyze_json_data(results)
            
            print(f"\n✅ Step 2 Complete!")
            print(f"📊 Results: {stats['successful']} successful, {stats['failed']} failed")
            print(f"📈 Success rate: {stats['success_rate']}%")
            print(f"📝 Total text: {stats['total_characters']:,} characters")
            print(f"📄 Average per article: {stats['average_chars_per_article']} characters")
            print(f"💾 Saved to: {demo_results_file.name}")
            
            return demo_results_file
        else:
            print("❌ Failed to save results")
            return False
    
    def step_3_demo_summary(self, sitemap_file, results_file):
        """Step 3: Generate demo summary"""
        
        print(f"\n📋 STEP 3: Demo Summary")
        print("=" * 50)
        
        try:
            file_handler = FileHandler()
            
            # Load sitemap data
            sitemap_data = file_handler.load_json(sitemap_file)
            sitemap_stats = len(sitemap_data) if sitemap_data else 0
            
            # Load results data
            results_data = file_handler.load_json(results_file)
            results_stats = file_handler.analyze_json_data(results_data) if results_data else {}
            
            # Create summary
            summary = {
                'demo_info': {
                    'title': 'FT Scraper Demo Pipeline - August 2025',
                    'completed_at': datetime.now().isoformat(),
                    'target_period': 'August 2025',
                    'article_limit': self.demo_config['max_articles']
                },
                'step_1_discovery': {
                    'target_sitemaps': len(self.demo_config['target_sitemaps']),
                    'total_entries_found': sitemap_stats,
                    'output_file': sitemap_file.name
                },
                'step_2_scraping': {
                    'articles_processed': results_stats.get('total_count', 0),
                    'successful_extractions': results_stats.get('successful', 0),
                    'failed_extractions': results_stats.get('failed', 0),
                    'success_rate_percent': results_stats.get('success_rate', 0),
                    'total_text_characters': results_stats.get('total_characters', 0),
                    'average_chars_per_article': results_stats.get('average_chars_per_article', 0),
                    'output_file': results_file.name
                },
                'demo_files': {
                    'sitemap_data': str(sitemap_file),
                    'scraped_articles': str(results_file),
                    'checkpoint': str(self.demo_dir / 'demo_checkpoint.json'),
                    'log_file': str(self.data_dir / 'logs' / 'demo_pipeline.log')
                }
            }
            
            # Save summary
            summary_file = self.demo_dir / 'demo_summary.json'
            file_handler.save_json(summary, summary_file)
            
            # Display summary
            print("🎯 DEMO PIPELINE COMPLETED SUCCESSFULLY!")
            print(f"📊 Discovered: {sitemap_stats} articles from August 2025 sitemaps")
            print(f"📰 Processed: {results_stats.get('total_count', 0)} articles")
            print(f"✅ Success rate: {results_stats.get('success_rate', 0)}%")
            print(f"📝 Text captured: {results_stats.get('total_characters', 0):,} characters")
            
            print(f"\n📁 Demo Files Created:")
            print(f"  • {sitemap_file.name} - Discovered articles")
            print(f"  • {results_file.name} - Scraped content")
            print(f"  • demo_summary.json - Complete summary")
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating summary: {e}")
            return False
    
    def run_complete_demo(self):
        """Run the complete demo pipeline"""
        
        start_time = time.time()
        
        print("🚀 FT SCRAPER DEMO PIPELINE")
        print("🎯 Target: August 2025 Articles (100 most recent)")
        print("⏱️  Estimated time: 3-5 minutes")
        print("=" * 60)
        
        try:
            # Step 1: Discover articles
            sitemap_file = self.step_1_discover_articles()
            if not sitemap_file:
                return False
            
            # Step 2: Scrape articles  
            results_file = self.step_2_scrape_articles(sitemap_file)
            if not results_file:
                return False
            
            # Step 3: Summary
            success = self.step_3_demo_summary(sitemap_file, results_file)
            
            # Final timing
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n⏱️  Total time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            print(f"📍 Demo files location: {self.demo_dir}")
            print(f"\n🎉 Demo pipeline completed {'successfully' if success else 'with errors'}!")
            
            return success
            
        except KeyboardInterrupt:
            print(f"\n⏸️  Demo pipeline interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Demo pipeline failed: {e}")
            logger.error(f"Demo pipeline failed: {e}")
            return False


def main():
    """Main demo function"""
    
    print("FT Scraper Demo Pipeline")
    print("Minimal resource demonstration of complete workflow")
    print()
    
    response = input("🎯 Run August 2025 demo pipeline? (y/N): ").lower().strip()
    if response != 'y':
        print("Demo cancelled.")
        return False
    
    demo = FTDemoPipeline()
    return demo.run_complete_demo()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
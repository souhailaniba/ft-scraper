#!/usr/bin/env python3
"""
Debug script to check article loading logic
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def debug_sitemap_data():
    """Debug sitemap data loading and year extraction"""
    
    sitemap_file = Path(__file__).parent.parent / 'data' / 'raw' / 'sitemap_data_test.json'
    
    print("🔍 Debugging Article Scraper Logic")
    print("=" * 50)
    print(f"Reading: {sitemap_file}")
    
    try:
        with open(sitemap_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Loaded {len(data)} entries")
        
        # Check each entry
        for i, item in enumerate(data):
            print(f"\n📄 Entry {i+1}:")
            print(f"   URL: {item.get('loc', 'NO URL')}")
            print(f"   lastmod: {item.get('lastmod', 'NO LASTMOD')}")
            print(f"   sitemap: {item.get('sitemap', 'NO SITEMAP')}")
            print(f"   errors: {item.get('errors', 'NO ERRORS')}")
            
            # Test year extraction methods
            print(f"   📅 Year extraction tests:")
            
            # Method 1: From sitemap filename
            sitemap = item.get('sitemap', '')
            year_from_sitemap = None
            if 'archive-' in sitemap:
                try:
                    year_part = sitemap.split('archive-')[1].split('-')[0]
                    year_from_sitemap = int(year_part)
                    print(f"      Method 1 (sitemap): {year_from_sitemap}")
                except (IndexError, ValueError) as e:
                    print(f"      Method 1 (sitemap): FAILED - {e}")
            else:
                print(f"      Method 1 (sitemap): NO ARCHIVE PATTERN")
            
            # Method 2: From lastmod timestamp
            year_from_lastmod = None
            if item.get('lastmod'):
                try:
                    lastmod_str = item['lastmod']
                    print(f"      lastmod value: '{lastmod_str}' (type: {type(lastmod_str)})")
                    
                    # Check if it's already in string format (from our new JSON saving)
                    if isinstance(lastmod_str, str):
                        if 'UTC' in lastmod_str:
                            # Parse "1995-11-18 02:01:30 UTC" format
                            dt = datetime.strptime(lastmod_str.replace(' UTC', ''), '%Y-%m-%d %H:%M:%S')
                            year_from_lastmod = dt.year
                        else:
                            # Try to convert string to timestamp
                            timestamp = int(lastmod_str)
                            year_from_lastmod = datetime.fromtimestamp(timestamp / 1000).year
                    elif isinstance(lastmod_str, (int, float)):
                        # Handle numeric timestamp
                        year_from_lastmod = datetime.fromtimestamp(lastmod_str / 1000).year
                    
                    print(f"      Method 2 (lastmod): {year_from_lastmod}")
                except (ValueError, OSError) as e:
                    print(f"      Method 2 (lastmod): FAILED - {e}")
            else:
                print(f"      Method 2 (lastmod): NO LASTMOD")
            
            # Final year
            final_year = year_from_sitemap or year_from_lastmod
            print(f"      ✅ Final year: {final_year}")
            
            # Filter test
            min_year = 2015
            passes_filter = final_year and final_year >= min_year
            print(f"      🔍 Passes {min_year}+ filter: {passes_filter}")
            
            print("-" * 30)
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_sitemap_data()
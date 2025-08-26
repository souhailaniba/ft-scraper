import json
import requests
import time

def simple_api_test():
    """Simple test with a few known good URLs"""
    
    print("🧪 Simple API Test")
    print("=" * 30)
    
    # Test with a few different types of URLs
    test_urls = [
        "https://www.ft.com/content/7845fc22-f811-11e5-96db-fc683b5e52db",  # From your data
        "https://www.ft.com",  # Homepage
        "https://www.ft.com/world",  # Section page
    ]
    
    # Check API health first
    print("🏥 Checking API health...")
    try:
        health_resp = requests.get("http://localhost:3000/health", timeout=10)
        print(f"   Status: {health_resp.status_code}")
        if health_resp.status_code == 200:
            health_data = health_resp.json()
            print(f"   Browser Ready: {health_data.get('browserReady')}")
        print()
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test each URL
    for i, url in enumerate(test_urls, 1):
        print(f"🧪 Test {i}: {url}")
        
        try:
            response = requests.post(
                "http://localhost:3000/scrape",
                json={"url": url},
                timeout=60
            )
            
            print(f"   HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('success', False)
                print(f"   API Success: {success}")
                
                if success:
                    html_length = len(result.get('html', ''))
                    print(f"   HTML Length: {html_length} chars")
                    
                    # Check if we got meaningful content
                    html = result.get('html', '')
                    if 'Financial Times' in html or 'ft.com' in html:
                        print(f"   ✅ Got FT content!")
                    else:
                        print(f"   ⚠️  HTML doesn't look like FT content")
                        
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"   ❌ API Error: {error}")
                    
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown')}")
                except:
                    print(f"   Error Text: {response.text[:200]}...")
                    
        except Exception as e:
            print(f"   ❌ Request Exception: {e}")
        
        print()
        time.sleep(2)  # Small delay between tests

def check_recent_urls_from_sitemap():
    """Check what recent URLs we actually have"""
    
    print("📊 Analyzing sitemap URLs...")
    
    try:
        with open('output.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Look for URLs from different time periods
        samples_by_sitemap = {}
        
        for item in data[:1000]:  # Check first 1000 entries
            if item.get('loc') and not item.get('errors'):
                sitemap = item.get('sitemap', 'Unknown')
                sitemap_name = sitemap.split('/')[-1] if sitemap else 'Unknown'
                
                if sitemap_name not in samples_by_sitemap:
                    samples_by_sitemap[sitemap_name] = []
                
                if len(samples_by_sitemap[sitemap_name]) < 2:  # Keep 2 samples per sitemap
                    samples_by_sitemap[sitemap_name].append(item['loc'])
        
        print("Sample URLs by sitemap:")
        for sitemap, urls in samples_by_sitemap.items():
            print(f"   {sitemap}:")
            for url in urls:
                print(f"     • {url}")
        
        return samples_by_sitemap
        
    except Exception as e:
        print(f"❌ Error reading sitemap: {e}")
        return {}

if __name__ == "__main__":
    # First check what URLs we have
    sitemap_samples = check_recent_urls_from_sitemap()
    
    print("\n" + "="*50 + "\n")
    
    # Then test the API
    simple_api_test()
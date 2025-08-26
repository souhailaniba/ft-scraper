import json
import requests
import time
from datetime import datetime
from urllib.parse import urlparse

def find_recent_articles(filename="output.json", limit=10):
    """Find recent articles to test with"""
    
    print("🔍 Finding recent articles for testing...")
    
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filter for recent articles (2020 onwards) and valid URLs
    recent_articles = []
    
    for item in data:
        if (item.get('loc') and 
            not item.get('errors') and
            item.get('lastmod')):
            
            # Convert timestamp to year (lastmod is in milliseconds)
            try:
                # Handle both string and numeric timestamps
                timestamp = item['lastmod']
                if isinstance(timestamp, str):
                    timestamp = int(timestamp)
                
                year = datetime.fromtimestamp(timestamp / 1000).year
                if year >= 2020:  # Recent articles only
                    recent_articles.append({
                        'url': item['loc'],
                        'year': year,
                        'lastmod': item['lastmod'],
                        'sitemap': item.get('sitemap', 'Unknown')
                    })
            except (ValueError, OSError):
                continue
    
    # Sort by year (newest first) and take the limit
    recent_articles.sort(key=lambda x: x['year'], reverse=True)
    test_articles = recent_articles[:limit]
    
    print(f"📊 Found {len(recent_articles)} articles from 2020+")
    print(f"🧪 Selected {len(test_articles)} for testing:")
    
    for i, article in enumerate(test_articles, 1):
        print(f"   {i}. {article['url']} ({article['year']})")
    
    return test_articles

def test_single_url_direct(url):
    """Test a single URL directly with the API"""
    
    print(f"\n🧪 Testing URL: {url}")
    
    try:
        response = requests.post(
            "http://localhost:3000/scrape",
            json={"url": url},
            timeout=60
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                html_length = len(result.get('html', ''))
                print(f"   ✅ Success! HTML length: {html_length} chars")
                return True
            else:
                print(f"   ❌ API returned success=false")
                return False
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error details: {error_data}")
            except:
                print(f"   Error text: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False

def test_api_health():
    """Test API health"""
    print("🏥 Testing API health...")
    
    try:
        response = requests.get("http://localhost:3000/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ API Status: {health.get('status')}")
            print(f"   🌐 Browser Ready: {health.get('browserReady')}")
            return health.get('browserReady', False)
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 FT API Troubleshooting Tool")
    print("=" * 50)
    
    # Test API health first
    if not test_api_health():
        print("❌ API is not healthy. Check your Node.js server.")
        exit(1)
    
    # Find recent articles
    test_articles = find_recent_articles(limit=5)
    
    if not test_articles:
        print("❌ No recent articles found for testing")
        exit(1)
    
    print(f"\n🧪 Testing {len(test_articles)} recent URLs...")
    print("=" * 50)
    
    success_count = 0
    for article in test_articles:
        if test_single_url_direct(article['url']):
            success_count += 1
        time.sleep(2)  # Delay between tests
    
    print(f"\n📊 Test Results:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {len(test_articles) - success_count}")
    print(f"   📈 Success Rate: {success_count/len(test_articles)*100:.1f}%")
    
    if success_count > 0:
        print(f"\n🎉 API is working! The issue was with old/invalid URLs.")
        print(f"💡 Recommendation: Filter your dataset to recent articles (2020+)")
    else:
        print(f"\n❌ API has issues. Check Node.js server logs for errors.")
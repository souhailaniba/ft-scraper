from newspaper import Article
import requests

def test_newspaper4k_methods():
    """Test what methods are available in newspaper4k"""
    
    print("🧪 Testing Newspaper4k Methods")
    print("=" * 40)
    
    # Create an article instance
    test_url = "https://www.ft.com/content/7845fc22-f811-11e5-96db-fc683b5e52db"
    article = Article(test_url)
    
    print(f"📰 Article object created for: {test_url}")
    print(f"📦 Article class: {article.__class__}")
    
    # Check available methods
    methods = [method for method in dir(article) if not method.startswith('_')]
    print(f"\n🔧 Available methods:")
    for method in sorted(methods):
        print(f"   • {method}")
    
    # Test specific methods we need
    important_methods = ['set_html', 'download_html', 'html', 'parse', 'nlp']
    print(f"\n🎯 Testing important methods:")
    
    for method in important_methods:
        has_method = hasattr(article, method)
        method_type = "method" if callable(getattr(article, method, None)) else "attribute"
        print(f"   • {method}: {'✅' if has_method else '❌'} ({method_type if has_method else 'missing'})")
    
    # Test with sample HTML
    sample_html = """
    <html>
    <head><title>Test Article</title></head>
    <body>
    <h1>Test Headline</h1>
    <p>This is a test paragraph with some content.</p>
    <p>This is another paragraph.</p>
    </body>
    </html>
    """
    
    print(f"\n🧪 Testing HTML extraction with sample content:")
    
    try:
        # Method 1: Try set_html if available
        if hasattr(article, 'set_html') and callable(article.set_html):
            print("   Trying method 1: set_html()")
            article.set_html(sample_html)
            article.parse()
            print(f"   ✅ Success! Title: '{article.title}', Text length: {len(article.text)} chars")
        
        # Method 2: Try setting html attribute directly
        elif hasattr(article, 'html'):
            print("   Trying method 2: html attribute")
            article.html = sample_html
            article.parse()
            print(f"   ✅ Success! Title: '{article.title}', Text length: {len(article.text)} chars")
        
        else:
            print("   ❌ No suitable method found for setting HTML")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test with real FT content
    print(f"\n🌐 Testing with real FT API content:")
    try:
        # Get HTML from our API
        api_response = requests.post(
            "http://localhost:3000/scrape",
            json={"url": test_url},
            timeout=30
        )
        
        if api_response.status_code == 200:
            result = api_response.json()
            if result.get('success'):
                html_content = result.get('html', '')
                print(f"   📥 Got HTML from API: {len(html_content)} chars")
                
                # Try to extract with newspaper4k
                fresh_article = Article(test_url)
                
                if hasattr(fresh_article, 'set_html') and callable(fresh_article.set_html):
                    fresh_article.set_html(html_content)
                else:
                    fresh_article.html = html_content
                
                fresh_article.parse()
                
                print(f"   📰 Extracted title: '{fresh_article.title}'")
                print(f"   📝 Text length: {len(fresh_article.text)} chars")
                print(f"   👥 Authors: {fresh_article.authors}")
                print(f"   📅 Publish date: {fresh_article.publish_date}")
                
                # Show first 200 chars of text
                if fresh_article.text:
                    preview = fresh_article.text[:200] + "..." if len(fresh_article.text) > 200 else fresh_article.text
                    print(f"   📖 Text preview: {preview}")
                
            else:
                print(f"   ❌ API returned error: {result.get('error')}")
        else:
            print(f"   ❌ API request failed: {api_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Real test failed: {e}")

if __name__ == "__main__":
    test_newspaper4k_methods()
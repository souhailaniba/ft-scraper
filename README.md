# FT Scraper

A professional web scraping system for Financial Times articles featuring paywall bypass, JavaScript rendering, scalable text extraction, and MongoDB integration.

## Overview

FT Scraper is an enterprise-grade system that discovers, scrapes, and processes Financial Times articles at scale. It handles the complex challenges of modern news scraping including Cloudflare protection, JavaScript-rendered content, and paywall restrictions.

### Key Capabilities

- **Comprehensive Discovery**: Automatically discovers 1M+ articles from FT sitemaps
- **Paywall Bypass**: Uses bypass-paywalls Chrome extension for full article access
- **JavaScript Rendering**: Puppeteer-based scraping handles dynamic content
- **High-Quality Extraction**: newspaper4k library for clean article text
- **Scalable Processing**: Multi-threaded architecture with configurable workers
- **Data Storage**: JSON files and optional MongoDB integration
- **Production Ready**: Professional logging, error handling, and recovery mechanisms

## System Architecture

```
ft_scraper/
├── README.md                     # Project documentation
├── requirements.txt              # Python dependencies
├── config/
│   └── settings.py               # Configuration settings
├── src/
│   ├── scrapers/
│   │   ├── sitemap_scraper.py    # Sitemap discovery and parsing
│   │   └── article_scraper.py    # Article content scraping
│   ├── extractors/
│   │   └── text_extractor.py     # Text extraction with newspaper4k
│   └── utils/
│       ├── logger.py             # Logging utilities
│       ├── file_handler.py       # JSON file operations
│       └── mongodb_handler.py    # MongoDB operations
├── server/
│   ├── server.js                 # Node.js API server with Puppeteer
│   └── package.json              # Node.js dependencies
├── scripts/
│   ├── run_sitemap_scraper.py    # Sitemap scraping CLI
│   ├── run_article_scraper.py    # Article scraping CLI
│   ├── run_demo_pipeline.py      # Demo workflow
│   ├── json_to_mongodb.py        # MongoDB import utility
│   └── query_mongodb.py          # MongoDB query utility
├── data/
│   ├── raw/                      # Discovered article URLs
│   ├── processed/                # Scraped article content
│   ├── demo/                     # Demo pipeline outputs
│   └── logs/                     # Application logs
└── tests/
    └── (test files)
```

## Prerequisites

### Required Software
- **Python 3.8+**
- **Node.js 16+**
- **Chrome/Chromium browser**
- **bypass-paywalls Chrome extension**

### Optional Software
- **MongoDB** (for advanced data storage and analysis)

## Installation

### 1. Clone and Setup Project
```bash
git clone <repository-url>
cd ft_scraper
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Node.js Dependencies
```bash
cd server
npm install
cd ..
```

### 4. Configure Extension Path
Update `config/settings.py` with your bypass-paywalls extension path:
```python
BYPASS_PAYWALLS_EXTENSION_PATH = "path/to/your/bypass-paywalls-chrome-clean-master"
```

## Quick Start

### Demo Pipeline (5 minutes)
Run the complete workflow with minimal resources:

```bash
cd scripts
python run_demo_pipeline.py
```

This demonstrates the entire system by processing August 2025 articles and scraping 100 recent articles.

### Manual Workflow

#### 1. Start the API Server (Terminal 1)
```bash
cd server
node server.js
```

#### 2. Discover/Scrape Articles (Terminal 2)
```bash
cd scripts

# Get recent articles (recommended)
python run_sitemap_scraper.py --limit 500

# Or get all articles (1M+, takes longer)
python run_sitemap_scraper.py
```

#### 3. Scrape Articles
```bash
# Test with 5 articles
python run_article_scraper.py --test

# Process 100 articles
python run_article_scraper.py --limit 100

# Process all discovered articles
python run_article_scraper.py
```

## Usage Examples

### Sitemap Discovery (Sitemap Scraping)
```bash
# Quick test with limited sitemaps
python run_sitemap_scraper.py --test

# Get 1000 recent articles
python run_sitemap_scraper.py --limit 1000

# Full sitemap crawl (1M+ articles)
python run_sitemap_scraper.py
```

### Article Scraping
```bash
# Test mode (5 most recent articles)
python run_article_scraper.py --test

# Custom limits and filters
python run_article_scraper.py --limit 50 --year 2020

# Use specific sitemap file
python run_article_scraper.py --limit 20 --input ../data/raw/sitemap_data_limit_500.json

# Skip confirmation prompt
python run_article_scraper.py --limit 10 --no-confirm
```

### MongoDB Integration (Optional)
```bash
# Import (scraped_sitemaps) JSON data to MongoDB
python json_to_mongodb.py ../data/demo/demo_sitemap_august2025.json --type sitemap

# Import (scraped_articles) JSON data to MongoDB
python json_to_mongodb.py ../data/demo/demo_scraped_articles_august2025.json

# Query database statistics
python query_mongodb.py --stats

# Find successful articles
python query_mongodb.py --successful --limit 20

# Custom queries
python query_mongodb.py --query '{"text_length": {"$gt": 10000}}'
```

## Configuration

Key settings in `config/settings.py`:

```python
# API Settings
API_URL = "http://localhost:3000"
DEFAULT_MAX_WORKERS = 3

# Article Filtering
MIN_ARTICLE_YEAR = 2015
DEFAULT_ARTICLE_LIMIT = None

# Browser Configuration
BYPASS_PAYWALLS_EXTENSION_PATH = "path/to/extension"
USER_AGENT = "Mozilla/5.0..."

# File Paths
SITEMAP_OUTPUT_FILE = "data/raw/sitemap_data.json"
SCRAPED_ARTICLES_FILE = "data/processed/scraped_articles.json"
```

## Performance

### Typical Results
- **Discovery Speed**: 1000+ sitemaps processed in 2-5 minutes
- **Scraping Speed**: 100-200 articles per hour (with respectful rate limiting)
- **Success Rate**: 75-100% depending on article age (2025 articles: 95-100%)
- **Text Quality**: Average 4,000-12,000 characters per article
- **Storage**: ~1MB per 1000 articles (JSON), ~500MB for full dataset

### Scaling Recommendations
- **Workers**: 1-5 (higher may trigger rate limiting)
- **Batch Size**: 50-500 articles for testing, unlimited for production
- **Rate Limiting**: Built-in 0.5s delays between requests
- **Memory**: 2-4GB RAM for full dataset processing

## Output Format

### Sitemap Data
```json
{
  "loc": "https://www.ft.com/content/...",
  "lastmod": 1693094400000,
  "image_loc": "http://...",
  "sitemap": "https://www.ft.com/sitemaps/archive-2025-8.xml",
  "sitemap_size_mb": 0.5,
  "download_date": 1693094400000
}
```

### Scraped Articles
```json
{
  "url": "https://www.ft.com/content/...",
  "success": true,
  "title": "Article Title",
  "text": "Full article text content...",
  "authors": ["Author Name"],
  "publish_date": "2025-08-23T10:30:00",
  "text_length": 11777,
  "scraped_at": "2025-08-25T12:57:00",
  "top_image": "https://..."
}
```

## Troubleshooting

### Common Issues

**API Connection Errors:**
- Ensure Node.js server is running on port 3000
- Check firewall settings and port availability
- Verify API health: `curl http://localhost:3000/health`

**Low Success Rates:**
- Check bypass-paywalls extension path in config
- Try filtering for more recent articles (--year 2020)
- Reduce worker count to avoid rate limiting

**Extension Loading Issues:**
- Verify extension path exists and is correct
- Ensure extension folder contains manifest.json
- Try running server with headless: false for debugging

**Memory Issues:**
- Reduce MAX_WORKERS (try 1-2)
- Process articles in smaller batches using --limit
- Monitor system memory during large runs

### Log Files
Check logs for detailed error information:
- `data/logs/ft_scraper.log` - General application logs
- `data/logs/sitemap_scraper.log` - Sitemap discovery logs
- `data/logs/article_scraper.log` - Article scraping logs
- `data/logs/demo_pipeline.log` - Demo pipeline logs

## Development

### Project Structure
The system follows clean architecture principles:
- **Separation of concerns**: Each module has a specific responsibility
- **Dependency injection**: Configuration managed centrally
- **Error handling**: Comprehensive logging and graceful failure recovery
- **Testability**: Modular design supports unit testing

### Adding Features
- **New scrapers**: Extend base classes in `src/scrapers/`
- **New extractors**: Add to `src/extractors/` following newspaper4k pattern
- **New storage backends**: Follow `file_handler.py` and `mongodb_handler.py` patterns
- **New CLI tools**: Add to `scripts/` with argparse configuration

### Testing
```bash
# Test individual components
python -m pytest tests/

# Run demo pipeline for integration testing
python scripts/run_demo_pipeline.py
```

## Legal Considerations

This tool is designed for educational and research purposes. Users should:

- Respect Financial Times' terms of service
- Use reasonable rate limiting to avoid server overload
- Consider subscribing to FT for commercial usage
- Comply with applicable copyright and data protection laws
- Review robots.txt and site policies before large-scale scraping

## Contributing

1. Follow existing code style and patterns
2. Add appropriate error handling and logging
3. Update documentation for new features
4. Test thoroughly before submitting changes

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **Puppeteer** - Browser automation framework
- **newspaper4k** - Article text extraction library
- **bypass-paywalls** - Community extension for paywall circumvention
- **Express.js** - Web application framework for Node.js
- **MongoDB** - Document database for advanced storage needs

---

**Note**: This system demonstrates advanced web scraping techniques for educational purposes. Always ensure compliance with website terms of service and applicable laws when using automated scraping tools.
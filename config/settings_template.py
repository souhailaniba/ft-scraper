"""
Configuration template for FT Scraper
Copy this to settings.py and customize for your environment
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
LOGS_DIR = DATA_DIR / 'logs'

# API Settings
API_HOST = "localhost"
API_PORT = int(os.getenv('API_PORT', 3000))
API_URL = f"http://{API_HOST}:{API_PORT}"

# Scraping Settings
DEFAULT_MAX_WORKERS = int(os.getenv('MAX_WORKERS', 3))
DEFAULT_REQUEST_TIMEOUT = 45
DEFAULT_DELAY_BETWEEN_REQUESTS = 0.5
CHECKPOINT_FREQUENCY = 25

# Browser Settings - CUSTOMIZE THIS PATH
BYPASS_PAYWALLS_EXTENSION_PATH = os.getenv(
    'BYPASS_PAYWALLS_PATH',
    # Default path - UPDATE THIS FOR YOUR SYSTEM:
    r"C:\path\to\your\bypass-paywalls-chrome-clean-master"
    # Linux/Mac example: "/home/user/bypass-paywalls-chrome-clean-master"
)

# User agent for sitemap requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# File Settings
SITEMAP_OUTPUT_FILE = RAW_DATA_DIR / 'sitemap_data.json'
ARTICLE_URLS_FILE = RAW_DATA_DIR / 'article_urls.json'
SCRAPED_ARTICLES_FILE = PROCESSED_DATA_DIR / 'scraped_articles.json'

# Logging Settings
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'
LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# FT Scraping Settings
FT_SITEMAP_URL = "https://www.ft.com/sitemaps/index.xml"
FT_USER_AGENT = "ft-scraper/1.0 (+mailto:your-email@example.com)"  # Customize email

# Article Filtering Settings
MIN_ARTICLE_YEAR = 2015
DEFAULT_ARTICLE_LIMIT = None  # None for unlimited

# MongoDB Settings (optional - only if using MongoDB integration)
MONGODB_CONNECTION = os.getenv('MONGODB_CONNECTION', 'mongodb://localhost:27017/')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'ft_scraper')

# Rate Limiting (be respectful to FT servers)
REQUESTS_PER_MINUTE = 60
CONCURRENT_REQUESTS = DEFAULT_MAX_WORKERS

# Create directories if they don't exist
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Validation
if not os.path.exists(BYPASS_PAYWALLS_EXTENSION_PATH):
    print(f"WARNING: Extension path not found: {BYPASS_PAYWALLS_EXTENSION_PATH}")
    print("Please update BYPASS_PAYWALLS_EXTENSION_PATH in config/settings.py")
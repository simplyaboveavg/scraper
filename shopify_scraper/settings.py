# Ultra-minimal Scrapy settings for reliable cloud deployment
import os
from datetime import datetime

# Basic Scrapy configuration
BOT_NAME = "shopify_scraper"
SPIDER_MODULES = ["shopify_scraper.spiders"]
NEWSPIDER_MODULE = "shopify_scraper.spiders"

# Disable robots.txt
ROBOTSTXT_OBEY = False

# Prevent memory buildup and crashes
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 950  # ScrapyCloud limit
MEMUSAGE_WARNING_MB = 800

# Close idle connections
DOWNLOAD_TIMEOUT = 60
# Optimized concurrency for better performance
CONCURRENT_REQUESTS = 4              # Increased from 2 (2x faster)
CONCURRENT_REQUESTS_PER_DOMAIN = 1   # Keep at 1 for stability

# Reduce memory per request
DOWNLOAD_MAXSIZE = 10485760  # 10MB max per response
DOWNLOAD_WARNSIZE = 5242880   # 5MB warning

# Optimized delays (middleware adds more sophisticated randomization)
DOWNLOAD_DELAY = 2                   # Reduced from 3
RANDOMIZE_DOWNLOAD_DELAY = 0.5

# User agents for rotation (required by custom middleware)
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

# Simple headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'User-Agent': USER_AGENT_LIST[0]  # Default, will be rotated by middleware
}

# Enhanced retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# Custom retry delays (used by middleware)
RETRY_DELAY_MIN = 10
RETRY_DELAY_MAX = 60

# Prevent connection reuse issues
REACTOR_THREADPOOL_MAXSIZE = 20

# Disable cookies
COOKIES_ENABLED = False

# Simple pipelines
ITEM_PIPELINES = {
    'shopify_scraper.pipelines.ShopifyScraperPipeline': 300,
}

# S3 Export - Dynamic filename with current date/time
timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
FEEDS = {
    f's3://simplyaboveaverage-scrapy/raw-shopify/shopify_multi-{timestamp}.json': {
        'format': 'jsonlines',
        'encoding': 'utf8',
        'overwrite': True,
    }
}

# Basic settings
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = 'INFO'

# Enhanced middleware for rate limiting protection
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,  # Disable
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,  # Disable default, use custom
    'shopify_scraper.middlewares.ShopifyScraperDownloaderMiddleware': 543,
    'shopify_scraper.middlewares.RateLimitMiddleware': 544,
}

# Disable problematic features
AUTOTHROTTLE_ENABLED = False
HTTPCACHE_ENABLED = False
REDIRECT_ENABLED = True

# Disable all extensions that might cause issues
EXTENSIONS = {}

# Suppress warnings
import warnings
warnings.filterwarnings('ignore')
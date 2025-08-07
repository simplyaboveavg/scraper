# Scrapy settings for shopify_scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import os
import scrapy.utils.reactor
scrapy.utils.reactor.install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, OSError):
    # Running in Scrapy Cloud or .env not found
    pass

BOT_NAME = "shopify_scraper"

SPIDER_MODULES = ["shopify_scraper.spiders"]
NEWSPIDER_MODULE = "shopify_scraper.spiders"

# Completely disable robots.txt checking to avoid getting blocked
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# Reduced for better rate limiting compliance
CONCURRENT_REQUESTS = 2

# The download delay setting will honor only one of:
# Very conservative to avoid rate limiting
CONCURRENT_REQUESTS_PER_DOMAIN = 1
CONCURRENT_REQUESTS_PER_IP = 1

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "DNT": "1",
}

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 12
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403, 520, 521, 522, 523, 524, 525, 526, 527, 530]
RETRY_PRIORITY_ADJUST = -1

# Custom retry delay settings (used by CustomRetryMiddleware)
RETRY_DELAY_MIN = 10  # Minimum delay in seconds
RETRY_DELAY_MAX = 60  # Maximum delay in seconds

# Configure item pipelines
ITEM_PIPELINES = {
   "shopify_scraper.pipelines.ShopifyScraperPipeline": 300,
   "shopify_scraper.pipelines.JsonLinesExportPipeline": 400,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# More aggressive throttling to avoid rate limits
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 15  # Start with longer delays
AUTOTHROTTLE_MAX_DELAY = 180   # Allow longer max delays
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.3  # Lower concurrency target
AUTOTHROTTLE_DEBUG = True

# Additional rate limiting settings
DOWNLOAD_DELAY = float(os.getenv('DOWNLOAD_DELAY', '2.0'))  # Increased base delay
RANDOMIZE_DOWNLOAD_DELAY = True  # Add randomization to avoid patterns

# Enable and configure HTTP caching (disabled by default)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [403, 429, 500, 503]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# S3 Feeds configuration
FEEDS = {
    's3://simplyaboveaverage-scrapy/raw-shopify/%(name)s-%(time)s.json': {
        'format': 'jsonlines',
        'encoding': 'utf8',
        'overwrite': True,
        'indent': None,
        'ensure_ascii': False,
        'newline': '\n'
    }
}

# Add a random delay between requests
RANDOMIZE_DOWNLOAD_DELAY = True

# User Agent rotation
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# Crawl in BFO order (breadth-first) to avoid hitting the same domain too frequently
DEPTH_PRIORITY = 1
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'

# Download timeout - increased for browser mode requests
DOWNLOAD_TIMEOUT = 120  # 120 seconds timeout (browser mode can be slower)

# Disable redirect middleware to avoid following redirects that might lead to honeypots
REDIRECT_ENABLED = False

# Adjust log level
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# =============================================================================
# HTML FALLBACK AND BROWSER MODE SETTINGS
# =============================================================================

# Enable cookies for HTML collection pages (some stores require session cookies)
# This will be overridden per-request when needed
COOKIES_ENABLED = False  # Keep disabled by default, enable per-request for HTML fallback

# Additional headers for HTML collection page requests
HTML_COLLECTION_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

# Dupefilter settings - allow duplicate URLs for HTML fallback
DUPEFILTER_CLASS = 'scrapy.dupefilters.RFPDupeFilter'
DUPEFILTER_DEBUG = False

# Memory usage optimization for large HTML pages
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048  # 2GB limit
MEMUSAGE_WARNING_MB = 1536  # Warning at 1.5GB

# Stats collection for monitoring HTML vs JSON success rates
STATS_CLASS = 'scrapy.statscollectors.MemoryStatsCollector'

# =============================================================================
# ZYTE API CONFIGURATION
# =============================================================================

# Get Zyte API key from environment variables
ZYTE_API_KEY = os.getenv('ZYTE_API_KEY', '')

# Use the addon approach (recommended)
if ZYTE_API_KEY:
    # Reactor is configured in scrapy.cfg for EC2 deployment
    
    ADDONS = {
        "scrapy_zyte_api.Addon": 500,
    }
    
    # Default parameters for all Zyte API requests (lightweight by default)
    ZYTE_API_DEFAULT_PARAMS = {
        'httpResponseBody': True,
        'geolocation': 'US',
        # Note: browserHtml is NOT enabled by default - only when explicitly requested
        # This saves costs by using lightweight requests unless browser mode is needed
    }
    
    # Ensure proper authentication (API key as username, empty password)
    ZYTE_API_URL = 'https://api.zyte.com/v1/extract'
    
    # Advanced Zyte API configuration
    ZYTE_API_TRANSPARENT_MODE = True   # Enable transparent mode for better compatibility
    # ZYTE_API_BROWSER_HTML removed from global settings - controlled per request
    ZYTE_API_SESSION_MODE = 'persistent' # keep cookies/session between requests
    ZYTE_API_REQUEST_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    # Disable HTTP cache when using Zyte API (caches can interfere with proxying)
    HTTPCACHE_ENABLED = False
    
    # Middleware configuration with Zyte API (addon handles Zyte middlewares automatically)
    DOWNLOADER_MIDDLEWARES = {
        'shopify_scraper.middlewares.CustomRetryMiddleware': 500,
        'shopify_scraper.middlewares.ShopifyScraperDownloaderMiddleware': 543,
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
        'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
        'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': None,
        'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': None,
        # Don't use RandomUserAgentMiddleware with Zyte API (Zyte handles headers)
        'shopify_scraper.middlewares.RandomUserAgentMiddleware': None,
    }
    
    print(f"Zyte API enabled with addon")
else:
    # Fallback configuration without Zyte API
    DOWNLOADER_MIDDLEWARES = {
        'shopify_scraper.middlewares.RandomUserAgentMiddleware': 400,
        'shopify_scraper.middlewares.CustomRetryMiddleware': 500,
        'shopify_scraper.middlewares.ShopifyScraperDownloaderMiddleware': 543,
        'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
        'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
        'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': None,
        'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': None,
    }
    print("No Zyte API key found. Running without Zyte services.")

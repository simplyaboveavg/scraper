# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
import random
import time
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from scrapy.exceptions import IgnoreRequest

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class ShopifyScraperSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn't have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class ShopifyScraperDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Skip robots.txt requests to avoid getting blocked
        if request.url.endswith('/robots.txt'):
            raise IgnoreRequest(f"Skipping robots.txt request for {request.url}")

        # Get store URL from request meta if available
        store_url = request.meta.get('store_url', '')
        
        # Check if this store should be skipped due to failures
        if hasattr(spider, 'should_skip_store') and store_url and spider.should_skip_store(store_url):
            spider.logger.warning(f"[{store_url}] Middleware skipping request due to store failures")
            raise IgnoreRequest(f"Skipping request for failed store: {store_url}")

        # Add a more sophisticated delay system
        # Use a more variable delay to avoid detection patterns
        delay_factor = random.random()  # Between 0 and 1
        
        # More conservative delays for better rate limiting
        if delay_factor < 0.6:  # 60% of requests get a short delay
            delay = random.uniform(2, 6)
        elif delay_factor < 0.85:  # 25% get a medium delay
            delay = random.uniform(6, 12)
        else:  # 15% get a longer delay
            delay = random.uniform(12, 20)
            
        # Add extra delay for rate-limited stores
        if store_url and hasattr(spider, 'store_failures'):
            failure_count = spider.store_failures.get(store_url, 0)
            if failure_count > 0:
                # Add exponential backoff based on failure count
                extra_delay = min(failure_count * 5, 30)  # Max 30 seconds extra
                delay += extra_delay
                spider.logger.info(f"[{store_url}] Adding {extra_delay}s extra delay due to {failure_count} failures")
            
        time.sleep(delay)
        
        # Add a random referer if not already set
        if 'Referer' not in request.headers:
            # List of common referrers - expanded with more realistic options
            referrers = [
                # Search engines
                'https://www.google.com/search?q=clothing+store',
                'https://www.google.com/search?q=fashion+store',
                'https://www.google.com/search?q=mens+clothing',
                'https://www.google.com/search?q=womens+clothing',
                'https://www.google.com/search?q=tall+clothing',
                'https://www.google.com/search?q=big+and+tall+clothing',
                'https://www.bing.com/search?q=clothing+store',
                'https://www.bing.com/search?q=fashion+store',
                'https://search.yahoo.com/search?p=clothing+store',
                'https://duckduckgo.com/?q=clothing+store',
                
                # Social media
                'https://www.facebook.com/',
                'https://www.instagram.com/',
                'https://www.pinterest.com/search/pins/?q=fashion',
                'https://www.pinterest.com/search/pins/?q=clothing',
                'https://www.reddit.com/r/fashion',
                'https://www.reddit.com/r/malefashionadvice',
                'https://www.reddit.com/r/femalefashionadvice',
                'https://twitter.com/search?q=fashion',
                
                # Shopping sites
                'https://www.amazon.com/s?k=clothing',
                'https://www.shopstyle.com/',
                'https://www.nordstrom.com/',
                'https://www.macys.com/',
            ]
            request.headers['Referer'] = random.choice(referrers)
        
        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Check for rate limiting or blocking responses
        if response.status in [403, 429]:
            spider.logger.warning(f"Rate limited or blocked at {request.url} (status: {response.status})")
            
            # If this is a robots.txt request, skip it
            if request.url.endswith('/robots.txt'):
                raise IgnoreRequest(f"Skipping robots.txt request that returned {response.status}")
                
            # For other requests, retry with a longer delay
            # Get custom retry delay settings
            min_delay = spider.settings.getint('RETRY_DELAY_MIN', 10)
            max_delay = spider.settings.getint('RETRY_DELAY_MAX', 60)
            
            # For rate limiting, use a longer delay
            retry_delay = random.uniform(max_delay, max_delay * 2)
            spider.logger.info(f"Rate limited. Waiting {retry_delay:.2f} seconds before retrying...")
            time.sleep(retry_delay)
            
            # Create a new request with different headers
            new_request = request.copy()
            # Add or update headers to look more like a browser
            new_request.headers['User-Agent'] = random.choice(spider.settings.get('USER_AGENT_LIST', []))
            new_request.headers['Accept-Language'] = 'en-US,en;q=0.9'
            new_request.headers['Accept-Encoding'] = 'gzip, deflate, br'
            new_request.headers['Connection'] = 'keep-alive'
            new_request.headers['Upgrade-Insecure-Requests'] = '1'
            new_request.headers['Cache-Control'] = 'max-age=0'
            new_request.dont_filter = True
            
            return new_request

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Log the exception
        spider.logger.error(f"Exception for {request.url}: {exception}")
        
        # If it's an IgnoreRequest exception, just pass it through
        if isinstance(exception, IgnoreRequest):
            return None
            
        # For other exceptions, wait and retry
        # Get custom retry delay settings
        min_delay = spider.settings.getint('RETRY_DELAY_MIN', 10)
        max_delay = spider.settings.getint('RETRY_DELAY_MAX', 60)
        
        # Use a random delay between min and max
        retry_delay = random.uniform(min_delay, max_delay)
        spider.logger.info(f"Exception occurred. Waiting {retry_delay:.2f} seconds before retrying...")
        time.sleep(retry_delay)
        
        # Create a new request with different headers
        new_request = request.copy()
        new_request.headers['User-Agent'] = random.choice(spider.settings.get('USER_AGENT_LIST', []))
        new_request.dont_filter = True
        
        return new_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class RandomUserAgentMiddleware:
    """
    Middleware to rotate user agents from a predefined list
    """
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)
        
    def __init__(self, settings):
        self.user_agent_list = settings.get('USER_AGENT_LIST', [])
        
    def process_request(self, request, spider):
        if self.user_agent_list:
            # Don't change user agent if it's already been set by retry middleware
            if 'User-Agent' not in request.headers:
                request.headers['User-Agent'] = random.choice(self.user_agent_list)
        return None


class CustomRetryMiddleware(RetryMiddleware):
    """
    Custom retry middleware with exponential backoff
    """
    
    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES', 2)
        self.retry_http_codes = settings.getlist('RETRY_HTTP_CODES', [])
        
    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
            
        # Check if the response is a rate limit or other error that should be retried
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            # Calculate exponential backoff delay
            retry_count = request.meta.get('retry_times', 0)
            
            # Get custom retry delay settings
            min_delay = spider.settings.getint('RETRY_DELAY_MIN', 10)
            max_delay = spider.settings.getint('RETRY_DELAY_MAX', 60)
            
            # Exponential backoff with jitter
            base_delay = min(2 ** (retry_count + 1), max_delay)
            # Add more randomization to avoid detection patterns
            jitter_factor = 0.3 + random.random() * 0.7  # Between 0.3 and 1.0
            delay = max(min_delay, base_delay * jitter_factor)
            
            spider.logger.warning(f"Retrying {request.url} (failed with {response.status}), retry #{retry_count+1} with {delay:.2f}s delay")
            
            # Sleep with exponential backoff
            time.sleep(delay)
            
            # Create a new request with different headers
            new_request = self._retry(request, reason, spider)
            if new_request:
                # Add or update headers to look more like a browser
                new_request.headers['User-Agent'] = random.choice(spider.settings.get('USER_AGENT_LIST', []))
                new_request.headers['Accept-Language'] = 'en-US,en;q=0.9'
                new_request.headers['Accept-Encoding'] = 'gzip, deflate, br'
                new_request.headers['Connection'] = 'keep-alive'
                new_request.headers['Upgrade-Insecure-Requests'] = '1'
                new_request.headers['Cache-Control'] = 'max-age=0'
                
                # Add a random referer - expanded with more realistic options
                referrers = [
                    # Search engines
                    'https://www.google.com/search?q=clothing+store',
                    'https://www.google.com/search?q=fashion+store',
                    'https://www.google.com/search?q=mens+clothing',
                    'https://www.google.com/search?q=womens+clothing',
                    'https://www.google.com/search?q=tall+clothing',
                    'https://www.google.com/search?q=big+and+tall+clothing',
                    'https://www.bing.com/search?q=clothing+store',
                    'https://www.bing.com/search?q=fashion+store',
                    'https://search.yahoo.com/search?p=clothing+store',
                    'https://duckduckgo.com/?q=clothing+store',
                    
                    # Social media
                    'https://www.facebook.com/',
                    'https://www.instagram.com/',
                    'https://www.pinterest.com/search/pins/?q=fashion',
                    'https://www.pinterest.com/search/pins/?q=clothing',
                    'https://www.reddit.com/r/fashion',
                    'https://www.reddit.com/r/malefashionadvice',
                    'https://www.reddit.com/r/femalefashionadvice',
                    'https://twitter.com/search?q=fashion',
                    
                    # Shopping sites
                    'https://www.amazon.com/s?k=clothing',
                    'https://www.shopstyle.com/',
                    'https://www.nordstrom.com/',
                    'https://www.macys.com/',
                ]
                new_request.headers['Referer'] = random.choice(referrers)
                
                return new_request
            
        return response
        
    def process_exception(self, request, exception, spider):
        # If the exception is a connection error, retry with exponential backoff
        retry_count = request.meta.get('retry_times', 0)
        if retry_count < self.max_retry_times:
            # Get custom retry delay settings
            min_delay = spider.settings.getint('RETRY_DELAY_MIN', 10)
            max_delay = spider.settings.getint('RETRY_DELAY_MAX', 60)
            
            # Exponential backoff with jitter
            base_delay = min(2 ** (retry_count + 1), max_delay)
            # Add more randomization to avoid detection patterns
            jitter_factor = 0.3 + random.random() * 0.7  # Between 0.3 and 1.0
            delay = max(min_delay, base_delay * jitter_factor)
            
            spider.logger.warning(f"Connection error for {request.url}, retry #{retry_count+1} with {delay:.2f}s delay: {exception}")
            
            # Sleep with exponential backoff
            time.sleep(delay)
            
            # Create a new request with different headers
            new_request = self._retry(request, exception, spider)
            if new_request:
                # Add or update headers to look more like a browser
                new_request.headers['User-Agent'] = random.choice(spider.settings.get('USER_AGENT_LIST', []))
                new_request.headers['Accept-Language'] = 'en-US,en;q=0.9'
                new_request.headers['Accept-Encoding'] = 'gzip, deflate, br'
                new_request.headers['Connection'] = 'keep-alive'
                new_request.headers['Upgrade-Insecure-Requests'] = '1'
                new_request.headers['Cache-Control'] = 'max-age=0'
                
                # Add a random referer - expanded with more realistic options
                referrers = [
                    # Search engines
                    'https://www.google.com/search?q=clothing+store',
                    'https://www.google.com/search?q=fashion+store',
                    'https://www.google.com/search?q=mens+clothing',
                    'https://www.google.com/search?q=womens+clothing',
                    'https://www.google.com/search?q=tall+clothing',
                    'https://www.google.com/search?q=big+and+tall+clothing',
                    'https://www.bing.com/search?q=clothing+store',
                    'https://www.bing.com/search?q=fashion+store',
                    'https://search.yahoo.com/search?p=clothing+store',
                    'https://duckduckgo.com/?q=clothing+store',
                    
                    # Social media
                    'https://www.facebook.com/',
                    'https://www.instagram.com/',
                    'https://www.pinterest.com/search/pins/?q=fashion',
                    'https://www.pinterest.com/search/pins/?q=clothing',
                    'https://www.reddit.com/r/fashion',
                    'https://www.reddit.com/r/malefashionadvice',
                    'https://www.reddit.com/r/femalefashionadvice',
                    'https://twitter.com/search?q=fashion',
                    
                    # Shopping sites
                    'https://www.amazon.com/s?k=clothing',
                    'https://www.shopstyle.com/',
                    'https://www.nordstrom.com/',
                    'https://www.macys.com/',
                ]
                new_request.headers['Referer'] = random.choice(referrers)
                
                return new_request
        
        return None

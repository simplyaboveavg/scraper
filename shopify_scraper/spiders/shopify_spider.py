import scrapy
import json
import os
import time
import random
from urllib.parse import urljoin
from twisted.internet import reactor
from twisted.internet.task import deferLater
from scrapy.exceptions import IgnoreRequest
from shopify_scraper.items import ShopifyProductItem


class ShopifySpider(scrapy.Spider):
    name = 'shopify_multi'

    BATCH_SIZE = 10
    INTER_STORE_DELAY_MIN = 60
    INTER_STORE_DELAY_MAX = 120
    INTER_BATCH_DELAY_MIN = 300
    INTER_BATCH_DELAY_MAX = 600
    
    # Per-store resilience settings
    MAX_STORE_FAILURES = 3  # Max consecutive failures before skipping store
    STORE_TIMEOUT = 300     # Max time to spend on a single store (seconds)
    MAX_PAGES_PER_STORE = 100  # Safety limit to prevent infinite loops

    # Hard error statuses that should immediately trigger browser mode
    HARD_ERROR_STATUSES = {403, 404, 429}

    # Two-phase processing: lightweight first, then browser mode for failed stores
    BROWSER_MODE_RETRY = True  # Enable browser mode retry phase
    
    PROGRESS_FILE = 'scraping_progress.json'
    FAILED_STORES_FILE = 'failed_stores.json'

    def __init__(self, store_url=None, batch_size=None, resume=False, stores_file=None, *args, **kwargs):
        super(ShopifySpider, self).__init__(*args, **kwargs)

        if batch_size:
            self.BATCH_SIZE = int(batch_size)

        self.completed_stores = set()
        self.failed_stores = set()  # Track stores that failed too many times
        self.store_failures = {}    # Track failure count per store
        self.store_start_times = {} # Track when we started each store
        self.current_batch = []
        self.all_stores = []
        self.browser_mode_phase = False  # Track if we're in browser mode retry phase
        self.original_store_count = 0    # Track original number of stores

        if resume and os.path.exists(self.PROGRESS_FILE):
            self.load_progress()
            self.logger.info(f"Resuming scrape. {len(self.completed_stores)} stores already completed.")

        if store_url:
            self.all_stores = [store_url]
            self.logger.info(f"Single store mode: Scraping {store_url}")
        elif stores_file and os.path.exists(stores_file):
            self.load_stores_from_file(stores_file)
            self.logger.info(f"Loaded {len(self.all_stores)} stores from {stores_file}")
        else:
            stores_file = 'shopify_scraper/shopify_stores.json'
            if os.path.exists(stores_file):
                self.load_stores_from_file(stores_file)
                self.logger.info(f"Loaded {len(self.all_stores)} stores from {stores_file}")
            else:
                self.all_stores = [
                    'https://dolcevita.com',
                   
                ]
                self.logger.info(f"Using default list of {len(self.all_stores)} stores")

        if resume:
            self.all_stores = [store for store in self.all_stores if store not in self.completed_stores]

        self.prepare_next_batch()

    def load_stores_from_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if isinstance(data, dict) and 'stores' in data:
                stores = data['stores']
            elif isinstance(data, list):
                stores = data
            else:
                self.logger.error(f"Unknown format in {file_path}")
                return

            self.all_stores = []
            for store in stores:
                store = store.rstrip('/')
                if not store.startswith(('http://', 'https://')):
                    store = f'https://{store}'
                self.all_stores.append(store)

        except Exception as e:
            self.logger.error(f"Error loading stores from {file_path}: {e}")
            self.all_stores = []

    def prepare_next_batch(self):
        remaining = len(self.all_stores)
        if remaining == 0:
            self.logger.info("No more stores to scrape!")
            return

        batch_size = min(self.BATCH_SIZE, remaining)
        self.current_batch = self.all_stores[:batch_size]
        self.all_stores = self.all_stores[batch_size:]

        self.logger.info(f"Prepared batch of {len(self.current_batch)} stores. {len(self.all_stores)} stores remaining.")

    def load_progress(self):
        try:
            if os.path.exists(self.PROGRESS_FILE):
                with open(self.PROGRESS_FILE, 'r') as f:
                    data = json.load(f)
                    self.completed_stores = set(data.get('completed_stores', []))
        except Exception as e:
            self.logger.error(f"Error loading progress: {e}")
            self.completed_stores = set()

    def save_progress(self):
        try:
            with open(self.PROGRESS_FILE, 'w') as f:
                json.dump({
                    'completed_stores': list(self.completed_stores),
                    'timestamp': time.time()
                }, f)
        except Exception as e:
            self.logger.error(f"Error saving progress: {e}")

    def save_failed_stores(self):
        """Save failed stores for browser mode retry"""
        try:
            failed_data = {
                'failed_stores': list(self.failed_stores),
                'store_failures': self.store_failures,
                'timestamp': time.time(),
                'phase': 'browser_mode_retry'
            }
            with open(self.FAILED_STORES_FILE, 'w') as f:
                json.dump(failed_data, f, indent=2)
            self.logger.info(f"Saved {len(self.failed_stores)} failed stores for browser mode retry")
        except Exception as e:
            self.logger.error(f"Error saving failed stores: {e}")

    def load_failed_stores(self):
        """Load failed stores for browser mode retry"""
        try:
            if os.path.exists(self.FAILED_STORES_FILE):
                with open(self.FAILED_STORES_FILE, 'r') as f:
                    data = json.load(f)
                return data.get('failed_stores', [])
        except Exception as e:
            self.logger.error(f"Error loading failed stores: {e}")
        return []

    def should_use_browser_mode(self, store_url):
        """Check if we should use browser mode for this store"""
        return self.browser_mode_phase or store_url in self.failed_stores

    def start_browser_mode_retry(self):
        """Start the browser mode retry phase for failed stores"""
        if not self.BROWSER_MODE_RETRY or not self.failed_stores:
            self.logger.info("No failed stores to retry with browser mode")
            return None

        self.logger.info(f"=== STARTING BROWSER MODE RETRY PHASE ===")
        self.logger.info(f"Retrying {len(self.failed_stores)} failed stores with full browser rendering")
        
        # Save failed stores list
        self.save_failed_stores()
        
        # Switch to browser mode phase
        self.browser_mode_phase = True
        
        # Reset stores list with failed stores
        self.all_stores = list(self.failed_stores)
        self.failed_stores = set()  # Reset failed stores for retry
        self.store_failures = {}    # Reset failure counts
        
        # Prepare first batch of failed stores
        self.prepare_next_batch()
        
        if self.current_batch:
            return self.start_next_store(0)
        return None

    def start_requests(self):
        if not self.current_batch:
            self.logger.info("No stores to scrape!")
            return

        store_url = self.current_batch[0]
        phase_msg = "BROWSER MODE" if self.browser_mode_phase else "NORMAL SCRAPY"
        self.logger.info(f"Starting with store: {store_url} ({phase_msg})")

        if self.browser_mode_phase:
            # Phase 2: Start with HTML collection page using Zyte API
            yield self._html_listing_request(store_url, 0)
        else:
            # Phase 1: Start with normal Scrapy JSON request
            page = 1
            full_url = f"{store_url}/products.json?page={page}&limit=250"

            request_meta = {
                'dont_retry': False,
                'max_retry_times': 5,
                'store_url': store_url,
            }

            yield scrapy.Request(
                url=full_url,
                callback=self.parse,
                cb_kwargs={
                    'store_url': store_url,
                    'page': page,
                    'batch_index': 0
                },
                meta=request_meta,
                dont_filter=True
            )

    def sleep(self, seconds):
        if seconds > 45:
            half = seconds / 2
            self.logger.info(f"[heartbeat] Sleeping {seconds:.2f}s... pinging at {half:.2f}s to keep alive")
            reactor.callLater(half, lambda: self.logger.info(f"[heartbeat] Still alive... {half:.0f}s left"))
        return deferLater(reactor, seconds, lambda: None)

    def should_skip_store(self, store_url):
        """Check if we should skip a store due to failures or timeout"""
        # Check if store has failed too many times
        if store_url in self.failed_stores:
            return True
            
        # Check failure count
        failure_count = self.store_failures.get(store_url, 0)
        if failure_count >= self.MAX_STORE_FAILURES:
            self.logger.warning(f"[{store_url}] Skipping store after {failure_count} failures")
            self.failed_stores.add(store_url)
            return True
            
        # Check timeout
        if store_url in self.store_start_times:
            elapsed = time.time() - self.store_start_times[store_url]
            if elapsed > self.STORE_TIMEOUT:
                self.logger.warning(f"[{store_url}] Skipping store after timeout ({elapsed:.1f}s)")
                self.failed_stores.add(store_url)
                return True
                
        return False

    def record_store_failure(self, store_url, error_msg="", hard=False):
        """Record a failure for a store"""
        self.store_failures[store_url] = self.store_failures.get(store_url, 0) + 1
        failure_count = self.store_failures[store_url]
        self.logger.warning(f"[{store_url}] Store failure #{failure_count}: {error_msg}")
        
        if hard or failure_count >= self.MAX_STORE_FAILURES:
            self.logger.error(f"[{store_url}] Store marked as failed (hard={hard})")
            self.failed_stores.add(store_url)

    def mark_store_completed(self, store_url):
        """Mark a store as successfully completed"""
        self.completed_stores.add(store_url)
        # Clean up tracking data
        self.store_failures.pop(store_url, None)
        self.store_start_times.pop(store_url, None)
        self.save_progress()
        self.logger.info(f"[{store_url}] Store completed successfully")

    def _html_listing_request(self, store_url, batch_index, page_url=None):
        """Create a browser mode request for HTML collection page fallback"""
        url = page_url or f"{store_url}/collections/all"
        self.logger.info(f"[{store_url}] Creating HTML collection fallback request: {url}")
        
        return scrapy.Request(
            url=url,
            callback=self.parse_collection_html,
            cb_kwargs={'store_url': store_url, 'batch_index': batch_index},
            meta={
                'store_url': store_url,
                '_html_fallback_tried': True,
                'zyte_api': {'browserHtml': True, 'geolocation': 'US'},
                'dont_retry': False,
            },
            dont_filter=True
        )

    def _product_json_or_html(self, product_url, store_url):
        """Try product.json first, fallback to HTML parsing"""
        product_json = product_url.rstrip('/') + '.json'
        return scrapy.Request(
            url=product_json,
            callback=self.parse_product_json,
            errback=lambda f: self._product_html_request(product_url, store_url),
            meta={'store_url': store_url, 'zyte_api': {'browserHtml': True, 'geolocation': 'US'}},
            dont_filter=True
        )

    def _product_html_request(self, product_url, store_url):
        """Create a browser mode request for individual product HTML parsing"""
        return scrapy.Request(
            url=product_url,
            callback=self.parse_product_html,
            meta={'store_url': store_url, 'zyte_api': {'browserHtml': True, 'geolocation': 'US'}},
            dont_filter=True
        )


    def parse(self, response, store_url, page, batch_index):
        # Check if we should skip this store due to failures or timeout
        if self.should_skip_store(store_url):
            self.logger.warning(f"[{store_url}] Skipping store due to previous failures or timeout")
            next_req = self.process_next_store(batch_index)
            if next_req:
                next_req.addCallback(self.schedule_next_request)
            return

        # Track store start time on first page
        if page == 1 and store_url not in self.store_start_times:
            self.store_start_times[store_url] = time.time()

        # Safety check for infinite loops
        if page > self.MAX_PAGES_PER_STORE:
            self.logger.warning(f"[{store_url}] Reached max pages limit ({self.MAX_PAGES_PER_STORE}), completing store")
            self.mark_store_completed(store_url)
            next_req = self.process_next_store(batch_index)
            if next_req:
                next_req.addCallback(self.schedule_next_request)
            return

        try:
            # Check for error responses
            if response.status >= 400:
                error_msg = f"HTTP {response.status}"
                if response.status == 429:
                    error_msg += " (Rate Limited)"
                elif response.status == 403:
                    error_msg += " (Forbidden)"
                elif response.status == 404:
                    error_msg += " (Not Found - may not be a Shopify store)"
                
                # Record failure and move to next store
                # Hard errors will be retried with Zyte API in Phase 2
                if response.status in self.HARD_ERROR_STATUSES:
                    self.record_store_failure(store_url, error_msg, hard=True)
                    self.logger.info(f"[{store_url}] Hard error {response.status}, will retry with Zyte API in Phase 2")
                else:
                    self.record_store_failure(store_url, error_msg)
                
                next_req = self.process_next_store(batch_index)
                if next_req:
                    next_req.addCallback(self.schedule_next_request)
                return

            data = response.json()
            products = data.get('products', [])

            self.logger.info(f"[{store_url}] Processing page {page} with {len(products)} products")

            if not products:
                self.logger.info(f"[{store_url}] No more products found on page {page}. Done with this store.")
                self.mark_store_completed(store_url)
                next_req = self.process_next_store(batch_index)
                if next_req:
                    next_req.addCallback(self.schedule_next_request)
                return

            for product in products:
                item = ShopifyProductItem()
                item['store'] = store_url
                item['id'] = product.get('id')
                item['title'] = product.get('title')
                item['handle'] = product.get('handle')
                item['vendor'] = product.get('vendor')
                item['product_type'] = product.get('product_type')
                item['tags'] = product.get('tags')
                item['variants'] = product.get('variants')
                item['images'] = product.get('images')  # Keep original images array
                item['body_html'] = product.get('body_html')
                
                # Extract up to 4 individual image URLs
                images = product.get('images', [])
                item['image_url'] = images[0].get('src') if len(images) > 0 else None
                item['image_url_2'] = images[1].get('src') if len(images) > 1 else None
                item['image_url_3'] = images[2].get('src') if len(images) > 2 else None
                item['image_url_4'] = images[3].get('src') if len(images) > 3 else None
                
                yield item

            # Continue to next page
            next_page = page + 1
            next_url = f"{store_url}/products.json?page={next_page}&limit=250"

            self.logger.info(f"[{store_url}] Queuing next page {next_page}")

            # Create request meta with browser mode if needed
            request_meta = {
                'dont_retry': False,
                'max_retry_times': 3,  # Reduced retries per page
                'store_url': store_url,  # Pass store_url in meta for middleware
            }
            
            # Add Zyte API browser mode if needed
            if self.should_use_browser_mode(store_url):
                request_meta['zyte_api'] = {
                    'browserHtml': True,
                    'geolocation': 'US',
                }

            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                cb_kwargs={
                    'store_url': store_url,
                    'page': next_page,
                    'batch_index': batch_index
                },
                meta=request_meta,
                dont_filter=True
            )

        except (ValueError, KeyError, TypeError) as e:
            # JSON parsing or data structure errors
            error_msg = f"Data parsing error on page {page}: {str(e)}"
            self.logger.error(f"[{store_url}] {error_msg}")
            self.record_store_failure(store_url, error_msg)
            next_req = self.process_next_store(batch_index)
            if next_req:
                next_req.addCallback(self.schedule_next_request)
        except Exception as e:
            # Any other unexpected errors
            error_msg = f"Unexpected error on page {page}: {str(e)}"
            self.logger.error(f"[{store_url}] {error_msg}")
            self.record_store_failure(store_url, error_msg)
            next_req = self.process_next_store(batch_index)
            if next_req:
                next_req.addCallback(self.schedule_next_request)


    def schedule_next_request(self, request):
            if request:
                self.logger.info(f"Scheduling next request: {request.url}")
                self.crawler.engine.crawl(request, self)

    def process_next_store(self, current_index):
            next_index = current_index + 1

            if next_index >= len(self.current_batch):
                if self.all_stores:
                    batch_delay = random.uniform(self.INTER_BATCH_DELAY_MIN, self.INTER_BATCH_DELAY_MAX)
                    self.logger.info(f"Batch completed. Waiting {batch_delay:.2f}s before starting next batch...")

                    d = self.sleep(batch_delay)
                    d.addCallback(lambda _: self.prepare_next_batch_and_start())
                    return d  # ✅ Return the deferred so Scrapy keeps running

                # Check if we should start browser mode retry phase
                if not self.browser_mode_phase and self.failed_stores and self.BROWSER_MODE_RETRY:
                    self.logger.info(f"=== PHASE 1 COMPLETE ===")
                    self.logger.info(f"Completed: {len(self.completed_stores)} stores")
                    self.logger.info(f"Failed: {len(self.failed_stores)} stores")
                    
                    # Start browser mode retry
                    return self.start_browser_mode_retry()
                
                # All processing complete
                total_completed = len(self.completed_stores)
                total_failed = len(self.failed_stores)
                phase_msg = "BROWSER MODE RETRY" if self.browser_mode_phase else "LIGHTWEIGHT MODE"
                
                self.logger.info(f"=== {phase_msg} COMPLETE ===")
                self.logger.info(f"Final Results - Completed: {total_completed}, Failed: {total_failed}")
                
                if self.browser_mode_phase:
                    self.logger.info("All processing phases complete!")
                else:
                    self.logger.info("Lightweight phase complete. No browser mode retry needed.")
                
                return None

            return self.start_next_store(next_index)


    def prepare_next_batch_and_start(self):
        self.prepare_next_batch()
        if self.current_batch:
            return self.start_next_store(0)
        return None

    def start_next_store(self, batch_index):
        if batch_index < len(self.current_batch):
            store_url = self.current_batch[batch_index]
            
            # Check if we should skip this store
            if self.should_skip_store(store_url):
                self.logger.warning(f"[{store_url}] Skipping store due to previous failures or timeout")
                return self.start_next_store(batch_index + 1)  # Skip to next store
            
            store_delay = random.uniform(self.INTER_STORE_DELAY_MIN, self.INTER_STORE_DELAY_MAX)
            phase_msg = "BROWSER MODE" if self.browser_mode_phase else "NORMAL SCRAPY"
            self.logger.info(f"Moving to next store: {store_url} ({phase_msg}). Waiting {store_delay:.2f}s...")

            def create_request(_):
                if self.browser_mode_phase:
                    # Phase 2: Use HTML collection page with Zyte API browser mode
                    return self._html_listing_request(store_url, batch_index)
                else:
                    # Phase 1: Use normal Scrapy with JSON endpoint
                    request_meta = {
                        'dont_retry': False,
                        'max_retry_times': 5,
                        'store_url': store_url,  # Pass store_url in meta for middleware
                    }
                    
                    return scrapy.Request(
                        url=f"{store_url}/products.json?page=1&limit=250",
                        callback=self.parse,
                        cb_kwargs={
                            'store_url': store_url,
                            'page': 1,
                            'batch_index': batch_index
                        },
                        meta=request_meta,
                        dont_filter=True
                    )

            d = self.sleep(store_delay)
            d.addCallback(create_request).addCallback(self.schedule_next_request)
            return d
        return None

    def parse_collection_html(self, response, store_url, batch_index):
        """Parse HTML collection page to extract product links"""
        self.logger.info(f"[{store_url}] Parsing HTML collection page: {response.url}")
        
        # Very forgiving CSS/XPath for Shopify product tiles
        links = set(response.css('a[href*="/products/"]::attr(href)').getall())
        if not links:
            self.logger.warning(f"[{store_url}] No product links found in HTML collection page")
            self.record_store_failure(store_url, "No product links in HTML", hard=True)
            next_req = self.process_next_store(batch_index)
            if next_req:
                next_req.addCallback(self.schedule_next_request)
            return

        self.logger.info(f"[{store_url}] HTML fallback: found {len(links)} product links")
        
        # Process each product link
        for href in links:
            # Clean up the URL (remove query parameters)
            url = response.urljoin(href.split('?')[0])
            yield self._product_json_or_html(url, store_url)

        # Optional: follow pagination if present
        next_href = response.css('a[rel="next"]::attr(href), a.pagination__next::attr(href)').get()
        if next_href:
            self.logger.info(f"[{store_url}] Found pagination, following to next page")
            yield self._html_listing_request(store_url, batch_index, response.urljoin(next_href))
        else:
            # No more pages, mark store as completed
            self.logger.info(f"[{store_url}] HTML collection parsing complete")
            self.mark_store_completed(store_url)
            next_req = self.process_next_store(batch_index)
            if next_req:
                next_req.addCallback(self.schedule_next_request)

    def parse_product_json(self, response):
        """Parse individual product JSON endpoint"""
        store_url = response.meta['store_url']
        
        try:
            data = response.json().get('product', {})
            if not data:
                # Drop into HTML parsing for this product
                prod_url = response.url.rsplit('.json', 1)[0]
                self.logger.info(f"[{store_url}] Product JSON empty, trying HTML: {prod_url}")
                yield self._product_html_request(prod_url, store_url)
                return

            # Successfully got product data from JSON
            yield from self._yield_shopify_item(store_url, data)
            
        except (ValueError, KeyError, TypeError) as e:
            # JSON parsing failed, try HTML
            prod_url = response.url.rsplit('.json', 1)[0]
            self.logger.warning(f"[{store_url}] Product JSON parsing failed, trying HTML: {str(e)}")
            yield self._product_html_request(prod_url, store_url)

    def parse_product_html(self, response):
        """Parse individual product HTML page for embedded JSON"""
        store_url = response.meta['store_url']
        self.logger.info(f"[{store_url}] Parsing product HTML: {response.url}")
        
        # Try common embedded JSON locations
        json_candidates = response.css('script[type="application/ld+json"]::text').getall()
        
        for txt in json_candidates:
            try:
                ld = json.loads(txt)
                if isinstance(ld, dict) and ld.get('@type') in ('Product', 'product'):
                    # Map LD+JSON to Shopify item structure (best-effort)
                    data = {
                        'id': ld.get('sku') or ld.get('productID') or None,
                        'title': ld.get('name'),
                        'vendor': ld.get('brand', {}).get('name') if isinstance(ld.get('brand'), dict) else ld.get('brand'),
                        'images': [{'src': i} for i in (ld.get('image') if isinstance(ld.get('image'), list) else [ld.get('image')]) if i],
                        'body_html': ld.get('description'),
                        'product_type': ld.get('category'),
                        'tags': None,
                        'variants': [],
                        'handle': response.url.rstrip('/').split('/products/')[-1],
                    }
                    
                    # Try to extract price from offers
                    offers = ld.get('offers', {})
                    if offers and isinstance(offers, dict):
                        price = offers.get('price')
                        if price:
                            data['variants'] = [{'price': price}]
                    
                    yield from self._yield_shopify_item(store_url, data)
                    return
                    
            except Exception as e:
                self.logger.debug(f"[{store_url}] Failed to parse LD+JSON: {str(e)}")
                continue
        
        # Try to find Shopify's embedded product JSON
        script_texts = response.css('script:contains("var meta")::text, script:contains("window.ShopifyAnalytics")::text').getall()
        for script_text in script_texts:
            try:
                # Look for product data in various Shopify script patterns
                if 'product' in script_text.lower():
                    # This is a simplified approach - in practice you might need more sophisticated parsing
                    self.logger.debug(f"[{store_url}] Found potential Shopify script, but parsing not implemented")
                    break
            except Exception:
                continue
        
        # If we get here, we couldn't parse the product
        self.logger.warning(f"[{store_url}] No parsable product JSON found in HTML: {response.url}")
        self.record_store_failure(store_url, "No parsable product JSON in HTML")

    def _yield_shopify_item(self, store_url, data):
        """Helper to create and yield a ShopifyProductItem from product data"""
        item = ShopifyProductItem()
        item['store'] = store_url
        item['id'] = data.get('id')
        item['title'] = data.get('title')
        item['handle'] = data.get('handle')
        item['vendor'] = data.get('vendor')
        item['product_type'] = data.get('product_type')
        item['tags'] = data.get('tags')
        item['variants'] = data.get('variants', [])
        item['images'] = data.get('images', [])
        item['body_html'] = data.get('body_html')
        
        # Extract up to 4 individual image URLs
        images = data.get('images', [])
        item['image_url'] = images[0].get('src') if len(images) > 0 else None
        item['image_url_2'] = images[1].get('src') if len(images) > 1 else None
        item['image_url_3'] = images[2].get('src') if len(images) > 2 else None
        item['image_url_4'] = images[3].get('src') if len(images) > 3 else None
        
        yield item

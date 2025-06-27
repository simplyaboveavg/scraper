import scrapy
import json
import os
import time
import random
from urllib.parse import urljoin
from twisted.internet import reactor
from twisted.internet.task import deferLater
from shopify_scraper.items import ShopifyProductItem


class ShopifySpider(scrapy.Spider):
    name = 'shopify_multi'

    BATCH_SIZE = 10
    INTER_STORE_DELAY_MIN = 60
    INTER_STORE_DELAY_MAX = 120
    INTER_BATCH_DELAY_MIN = 300
    INTER_BATCH_DELAY_MAX = 600

    PROGRESS_FILE = 'scraping_progress.json'

    def __init__(self, store_url=None, batch_size=None, resume=False, stores_file=None, *args, **kwargs):
        super(ShopifySpider, self).__init__(*args, **kwargs)

        if batch_size:
            self.BATCH_SIZE = int(batch_size)

        self.completed_stores = set()
        self.current_batch = []
        self.all_stores = []

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

    def start_requests(self):
        if not self.current_batch:
            self.logger.info("No stores to scrape!")
            return

        store_url = self.current_batch[0]
        self.logger.info(f"Starting with store: {store_url}")

        page = 1
        full_url = f"{store_url}/products.json?page={page}&limit=250"

        yield scrapy.Request(
            url=full_url,
            callback=self.parse,
            cb_kwargs={
                'store_url': store_url,
                'page': page,
                'batch_index': 0
            },
            meta={
                'dont_retry': False,
                'max_retry_times': 5,
            },
            dont_filter=True
        )

    def sleep(self, seconds):
        if seconds > 45:
            half = seconds / 2
            self.logger.info(f"[heartbeat] Sleeping {seconds:.2f}s... pinging at {half:.2f}s to keep alive")
            reactor.callLater(half, lambda: self.logger.info(f"[heartbeat] Still alive... {half:.0f}s left"))
        return deferLater(reactor, seconds, lambda: None)


    def parse(self, response, store_url, page, batch_index):
        try:
            data = response.json()
            products = data.get('products', [])

            self.logger.info(f"[{store_url}] Processing page {page} with {len(products)} products")

            if not products:
                self.logger.info(f"[{store_url}] No more products found on page {page}. Done with this store.")
                self.completed_stores.add(store_url)
                self.save_progress()

                next_req = self.process_next_store(batch_index)
                if next_req:
                    next_req.addCallback(self.schedule_next_request)


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
                item['images'] = product.get('images')
                item['body_html'] = product.get('body_html')
                yield item

            next_page = page + 1
            next_url = f"{store_url}/products.json?page={next_page}&limit=250"

            self.logger.info(f"[{store_url}] Queuing next page {next_page}")

            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                cb_kwargs={
                    'store_url': store_url,
                    'page': next_page,
                    'batch_index': batch_index
                },
                meta={
                    'dont_retry': False,
                    'max_retry_times': 5,
                },
                dont_filter=True
            )

        except Exception as e:
            self.logger.error(f"[{store_url}] Error processing page {page}: {e}")
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

                self.logger.info("All stores processed! Scraping complete.")
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
            store_delay = random.uniform(self.INTER_STORE_DELAY_MIN, self.INTER_STORE_DELAY_MAX)
            self.logger.info(f"Moving to next store: {store_url}. Waiting {store_delay:.2f}s...")

            d = self.sleep(store_delay)
            d.addCallback(
                lambda _: scrapy.Request(
                    url=f"{store_url}/products.json?page=1&limit=250",
                    callback=self.parse,
                    cb_kwargs={
                        'store_url': store_url,
                        'page': 1,
                        'batch_index': batch_index
                    },
                    meta={
                        'dont_retry': False,
                        'max_retry_times': 5,
                    },
                    dont_filter=True
                )
            ).addCallback(self.schedule_next_request)
            return d
        return None
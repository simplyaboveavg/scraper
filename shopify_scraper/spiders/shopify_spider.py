import scrapy
import json
import os
import re
import time
from datetime import datetime
from shopify_scraper.items import ShopifyProductItem


def _data_file(filename):
    """Resolve path to a bundled data file (works locally and on ScrapyCloud/egg)."""
    try:
        import pkg_resources
        return pkg_resources.resource_filename('shopify_scraper', os.path.join('data', filename))
    except Exception:
        # Fallback to relative path for local dev
        return os.path.join(os.path.dirname(__file__), '..', 'data', filename)


class ShopifySpider(scrapy.Spider):
    name = 'shopify_multi'

    def __init__(self, store_url=None, stores_file=None, stores_json=None, *args, **kwargs):
        super(ShopifySpider, self).__init__(*args, **kwargs)

        self.stores = []
        self.store_products = {}  # Track products per store
        self.store_status = {}    # Track status per store
        self.failed_stores = []   # Track failures
        self.start_time = time.time()

        # Load vendor name mappings from JSON (no more hardcoded dict)
        self.vendor_names = self._load_vendor_names()

        # Load stores — priority order
        if store_url:
            # Single store mode
            self.stores = [store_url]
            self.logger.info(f"Single store mode: {store_url}")
        elif stores_json:
            # Load from JSON string (ScrapyCloud argument)
            self.load_stores_from_json_string(stores_json)
            self.logger.info(f"Loaded {len(self.stores)} stores from JSON string")
        elif stores_file and os.path.exists(stores_file):
            # Load from explicit file path
            self.load_stores_from_file(stores_file)
            self.logger.info(f"Loaded {len(self.stores)} stores from {stores_file}")
        else:
            # Default: load from bundled data file (no hardcoding needed)
            bundled = _data_file('shopify_stores.json')
            if os.path.exists(bundled):
                self.load_stores_from_file(bundled)
                self.logger.info(f"Loaded {len(self.stores)} stores from bundled data file")
            else:
                self.logger.error(f"No store source found! Tried: {bundled}")
                self.stores = []

    def _load_vendor_names(self):
        """Load vendor name mappings from bundled JSON file."""
        path = _data_file('vendor_names.json')
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            # Remove metadata keys (starting with _)
            return {k: v for k, v in data.items() if not k.startswith('_')}
        except FileNotFoundError:
            self.logger.warning(f"vendor_names.json not found at {path}, using empty mappings")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading vendor_names.json: {e}")
            return {}

    def load_stores_from_json_string(self, json_string):
        """Load stores from JSON string (for ScrapyCloud)"""
        try:
            data = json.loads(json_string)
            
            if isinstance(data, dict) and 'stores' in data:
                stores = data['stores']
            elif isinstance(data, list):
                stores = data
            else:
                self.logger.error(f"Unknown JSON format")
                return
            
            self.stores = []
            for store in stores:
                store = store.rstrip('/')
                if not store.startswith(('http://', 'https://')):
                    store = f'https://{store}'
                self.stores.append(store)
                
        except Exception as e:
            self.logger.error(f"Error loading stores from JSON string: {e}")
            self.stores = []
        
        # Mark all stores as pending
        for store in self.stores:
            self.store_status[store] = 'pending'

    def load_stores_from_file(self, file_path):
        """Load stores from JSON file"""
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

            self.stores = []
            for store in stores:
                store = store.rstrip('/')
                if not store.startswith(('http://', 'https://')):
                    store = f'https://{store}'
                self.stores.append(store)

        except Exception as e:
            self.logger.error(f"Error loading stores from {file_path}: {e}")
            self.stores = []
        
        # Mark all stores as pending
        for store in self.stores:
            self.store_status[store] = 'pending'
    
    def should_filter_product(self, product):
        """Filter out non-physical products"""
        title = product.get('title', '').lower()
        product_type = product.get('product_type', '').lower()
        tags = [tag.lower() for tag in product.get('tags', [])]
        
        # Non-physical product keywords
        filter_keywords = [
            'gift card', 'giftcard', 'gift certificate', 'giftcertificate',
            'store credit', 'storecredit', 'donation', 'donate',
            'sample pack', 'samplepack', 'membership', 'member',
            'digital download', 'digitaldownload', 'e-gift', 'egift',
            'insurance', 'warranty', 'service', 'subscription',
            'virtual', 'online', 'digital', 'download', 'ebook',
            'course', 'training', 'consultation', 'booking',
            'shipping protection', 'shippingprotection', 'protection'
        ]
        
        # Check title, product type, and tags
        all_text = f"{title} {product_type} {' '.join(tags)}"
        
        for keyword in filter_keywords:
            if keyword in all_text:
                return True
        
        return False
    
    def _domain_key(self, store_url):
        """Extract the domain key used for vendor_names.json lookup.

        Examples:
        - https://dolcevita.com → dolcevita
        - https://us.daughtersofindia.net → daughtersofindia
        - https://big-tall.com → big-tall
        """
        domain = store_url.replace('https://', '').replace('http://', '').replace('www.', '')
        parts = domain.split('.')
        # Strip common subdomains
        if len(parts) > 2 and parts[0].lower() in ('us', 'shop', 'store', 'en', 'uk', 'ca'):
            parts = parts[1:]
        return parts[0].lower()

    def extract_vendor_from_url(self, store_url):
        """
        Get clean vendor/brand name for a store URL.

        Priority:
        1. Lookup in vendor_names.json (covers all known stores)
        2. Smart auto-detection from domain name (for new stores)
        """
        try:
            key = self._domain_key(store_url)

            # 1. Check vendor_names.json
            if key in self.vendor_names:
                return self.vendor_names[key]

            # 2. Auto-detect: clean up domain name
            cleaned = key.replace('-', ' ').replace('_', ' ')
            # Split camelCase: "dolceVita" → "dolce Vita"
            cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
            # Space between numbers and letters: "100brawn" → "100 brawn"
            cleaned = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', cleaned)
            # Strip common suffixes that aren't part of the brand name
            for suffix in ('clothing', 'official', 'brand', 'shop', 'store', 'usa', 'nyc', 'jaipur'):
                cleaned = re.sub(rf'\b{suffix}\b', '', cleaned, flags=re.IGNORECASE)
            cleaned = ' '.join(cleaned.split())  # collapse whitespace

            vendor_name = ' '.join(word.capitalize() for word in cleaned.split())

            self.logger.info(
                f"Auto-detected vendor name for {store_url} → '{vendor_name}'. "
                f"Add '{key}': '{vendor_name}' to vendor_names.json to confirm or override."
            )
            return vendor_name

        except Exception as e:
            self.logger.warning(f"Could not extract vendor from URL {store_url}: {e}")
        return None

    def start_requests(self):
        """Generate initial requests for all stores"""
        for store_url in self.stores:
            url = f"{store_url}/products.json?limit=250&page=1"
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,  # ADD THIS
                meta={'store_url': store_url, 'page': 1},
                dont_filter=True
            )

    def handle_error(self, failure):
        """Handle request failures"""
        store_url = failure.request.meta.get('store_url', 'unknown')
        self.logger.error(f"❌ [{store_url}] Request failed: {failure.value}")
        
        # Track failed store
        self.failed_stores.append({
            'store': store_url,
            'error': str(failure.value),
            'type': failure.type.__name__
        })
        self.store_status[store_url] = 'failed'

    def parse(self, response):
        """Parse products.json response"""
        store_url = response.meta['store_url']
        page = response.meta['page']
        
        try:
            data = response.json()
            products = data.get('products', [])

            # Track products
            if store_url not in self.store_products:
                self.store_products[store_url] = 0
            self.store_products[store_url] += len(products)
            
            # Mark as in progress
            self.store_status[store_url] = 'in_progress'
            
            self.logger.info(f"[{store_url}] Page {page}: {len(products)} products")
            
            # Initialize quality tracking
            if not hasattr(self, 'quality_issues'):
                self.quality_issues = {
                    'no_images': 0,
                    'no_variants': 0,
                    'no_price': 0,
                    'filtered_non_physical': 0
                }
            
            # Process each product
            for product in products:
                # Filter out non-physical products
                if self.should_filter_product(product):
                    self.quality_issues['filtered_non_physical'] += 1
                    continue
                item = ShopifyProductItem()
                item['store'] = store_url
                item['id'] = product.get('id')
                item['title'] = product.get('title')
                item['handle'] = product.get('handle')
                item['vendor'] = product.get('vendor')
                item['vendor_clean'] = self.extract_vendor_from_url(store_url)
                item['product_type'] = product.get('product_type')
                # item['tags'] = product.get('tags')  # Removed - not used in downstream processing
                item['variants'] = product.get('variants', [])
                item['images'] = product.get('images', [])
                item['body_html'] = product.get('body_html')
                
                # Create product URL
                if item['handle']:
                    item['product_url'] = f"{store_url}/products/{item['handle']}"
                
                # Extract individual image URLs (up to 4)
                images = product.get('images', [])
                item['image_url'] = images[0].get('src') if len(images) > 0 else None
                item['image_url_2'] = images[1].get('src') if len(images) > 1 else None
                item['image_url_3'] = images[2].get('src') if len(images) > 2 else None
                item['image_url_4'] = images[3].get('src') if len(images) > 3 else None
                
                # Price information removed - using individual variant prices in flatten_lambda instead
                
                # Track data quality issues
                if not item.get('image_url'):
                    self.quality_issues['no_images'] += 1
                    self.logger.warning(f"⚠️ Product {item['id']} has no images")
                
                if not item.get('variants'):
                    self.quality_issues['no_variants'] += 1
                
                # Check if any variant has a price
                has_price = any(v.get('price') for v in item.get('variants', []))
                if not has_price:
                    self.quality_issues['no_price'] += 1
                
                yield item
            
            # Continue to next page if products were found
            if products:
                next_page = page + 1
                next_url = f"{store_url}/products.json?limit=250&page={next_page}"
                yield scrapy.Request(
                    url=next_url,
                        callback=self.parse,
                    errback=self.handle_error,
                    meta={'store_url': store_url, 'page': next_page},
                        dont_filter=True
                    )
            else:
                # Store completed
                self.store_status[store_url] = 'completed'
                self.logger.info(
                    f"✅ [{store_url}] COMPLETED - "
                    f"{self.store_products[store_url]} products"
                )
                
        except Exception as e:
            self.logger.error(f"❌ [{store_url}] Error parsing page {page}: {e}")
            self.store_status[store_url] = 'failed'
            self.failed_stores.append({
                'store': store_url,
                'error': str(e),
                'page': page
            })

    def closed(self, reason):
        """Generate detailed summary when spider closes"""
        duration = time.time() - self.start_time
        
        # Calculate stats
        completed = [s for s, status in self.store_status.items() if status == 'completed']
        failed = [s for s, status in self.store_status.items() if status == 'failed']
        pending = [s for s, status in self.store_status.items() if status == 'pending']
        total_products = sum(self.store_products.values())
        
        # Create detailed report
        report = {
            'run_info': {
                'completed_at': datetime.now().isoformat(),
                'duration_minutes': round(duration / 60, 1),
                'reason': reason
            },
            'summary': {
                'total_stores': len(self.stores),
                'completed': len(completed),
                'failed': len(failed),
                'pending': len(pending),
                'total_products': total_products,
                'avg_products_per_store': round(total_products / len(completed), 1) if completed else 0
            },
            'store_details': {
                store: {
                    'status': self.store_status.get(store, 'unknown'),
                    'products': self.store_products.get(store, 0)
                } for store in self.stores
            },
            'failed_stores': self.failed_stores
        }
        
        # Add quality issues to report
        if hasattr(self, 'quality_issues'):
            report['quality_issues'] = self.quality_issues
        
        # Log summary
        self.logger.info("=" * 80)
        self.logger.info("SCRAPE SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Duration: {report['run_info']['duration_minutes']} minutes")
        self.logger.info(f"Total Stores: {report['summary']['total_stores']}")
        self.logger.info(f"✅ Completed: {report['summary']['completed']}")
        self.logger.info(f"❌ Failed: {report['summary']['failed']}")
        self.logger.info(f"⏸️  Pending: {report['summary']['pending']}")
        self.logger.info(f"📦 Total Products: {report['summary']['total_products']}")
        self.logger.info(f"📊 Avg Products/Store: {report['summary']['avg_products_per_store']}")
        
        if completed:
            self.logger.info("")
            self.logger.info("COMPLETED STORES:")
            self.logger.info("-" * 80)
            for store in sorted(completed):
                count = self.store_products.get(store, 0)
                self.logger.info(f"  ✅ {store}: {count} products")
        
        if failed:
            self.logger.info("")
            self.logger.info("FAILED STORES:")
            self.logger.info("-" * 80)
            for store in failed:
                failure_info = next((f for f in self.failed_stores if f['store'] == store), {})
                error = failure_info.get('error', 'Unknown error')
                self.logger.info(f"  ❌ {store}: {error}")
        
        if pending:
            self.logger.info("")
            self.logger.info("PENDING STORES (never started):")
            self.logger.info("-" * 80)
            for store in pending:
                self.logger.info(f"  ⏸️  {store}")
        
        # Data quality issues
        if hasattr(self, 'quality_issues'):
            self.logger.info("")
            self.logger.info("DATA QUALITY ISSUES:")
            self.logger.info("-" * 80)
            self.logger.info(f"  Products missing images: {self.quality_issues['no_images']}")
            self.logger.info(f"  Products missing variants: {self.quality_issues['no_variants']}")
            self.logger.info(f"  Products missing prices: {self.quality_issues['no_price']}")
            self.logger.info(f"  Non-physical products filtered: {self.quality_issues['filtered_non_physical']}")
        
        self.logger.info("=" * 80)
        
        # Save report as JSON (locally - ScrapyCloud will have it in logs)
        report_file = f"scrape_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            self.logger.info(f"📄 Report saved to {report_file}")
        except Exception as e:
            self.logger.warning(f"Could not save report file: {e}")
        
        # Create failed stores file for easy retry
        if self.failed_stores:
            failed_urls = [f['store'] for f in self.failed_stores]
            retry_file = {
                'stores': failed_urls,
                'metadata': {
                    'original_run': datetime.now().isoformat(),
                    'reason': 'retry_failed_stores',
                    'failed_count': len(failed_urls)
                }
            }
            
            try:
                with open('failed_stores_retry.json', 'w') as f:
                    json.dump(retry_file, f, indent=2)
                self.logger.info(f"📄 Failed stores saved to failed_stores_retry.json")
                self.logger.info(f"To retry: scrapy crawl shopify_multi -a stores_file=failed_stores_retry.json")
            except Exception as e:
                self.logger.warning(f"Could not save failed stores file: {e}")

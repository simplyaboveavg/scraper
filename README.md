# Shopify Scraper

A production-ready Shopify store scraper with advanced rate limiting protection, comprehensive reporting, and enterprise-grade features.

## 📁 Project Structure

```
shopify_scraper/
├── shopify_scraper/          # Main scraper package
│   ├── spiders/              # Scrapy spiders
│   │   └── shopify_spider.py # Main spider with hardcoded stores
│   ├── items.py              # Data models with price extraction
│   ├── pipelines.py          # Data processing & S3 export
│   ├── middlewares.py        # Custom anti-blocking middlewares
│   └── settings.py           # Optimized Scrapy settings
├── store_filter/             # Store filtering utilities
│   └── filter_shopify_stores.py
├── data/                     # Data files
│   ├── master_store_list.txt # Master store list (EDIT THIS)
│   ├── shopify_stores.json   # Filtered Shopify stores
│   └── non_shopify_stores.json
├── update_spider_stores.py   # Update hardcoded stores in spider
├── generate_scrapycloud_args.py # Generate ScrapyCloud arguments
├── store_exports/            # Local exports
├── json_exports/             # JSON exports
└── venv/                     # Virtual environment
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
cd shopify_scraper
source venv/bin/activate
```

### 2. Update Store List (IMPORTANT!)
**⚠️ If you modify `data/master_store_list.txt`, you MUST rerun the filtering script:**

```bash
# After editing master_store_list.txt, run:
python store_filter/filter_shopify_stores.py
```

This ensures `data/shopify_stores.json` reflects your changes (additions/deletions).

### 3. Filter Shopify Stores
```bash
python store_filter/filter_shopify_stores.py
```

### 4. Run Scraper
```bash
# Single store test
scrapy crawl shopify_multi -a store_url=https://example.com

# All stores (hardcoded in spider)
scrapy crawl shopify_multi

# With custom store file (local development)
scrapy crawl shopify_multi -a stores_file=path/to/stores.json

# Deploy to ScrapyCloud
shub deploy
```

## 📊 Data Output

- **Format**: JSON Lines (.jsonl)
- **Location**: S3 bucket `s3://simplyaboveaverage-scrapy/raw-shopify/`
- **Fields**: 
  - **Basic**: id, title, handle, vendor, product_type, tags, variants, images, body_html, product_url
  - **Images**: image_url, image_url_2, image_url_3, image_url_4 (up to 4 images)
  - **Pricing**: price_min, price_max, compare_at_price_min, compare_at_price_max
  - **Metadata**: store, scrape_timestamp

## 📈 Comprehensive Reporting

The scraper generates detailed reports including:
- **Store Status**: Completed, failed, pending stores
- **Product Counts**: Total products per store
- **Data Quality**: Missing images, variants, prices
- **Performance**: Duration, success rates, error details
- **Retry Files**: Auto-generated `failed_stores_retry.json` for easy retry

## 🔧 Configuration

### Store List Format
```json
{
  "stores": [
    "store1.com",
    "store2.com"
  ]
}
```

### Environment Variables
- `LOG_LEVEL`: Set logging level (INFO, DEBUG, etc.)

## 🚀 Enterprise Features

- ✅ **Advanced Rate Limiting**: Custom middleware with exponential backoff
- ✅ **Memory Management**: Prevents crashes with 950MB limit monitoring
- ✅ **User Agent Rotation**: 5 different user agents to avoid detection
- ✅ **Comprehensive Tracking**: Real-time store status and product counting
- ✅ **Data Quality Monitoring**: Tracks missing images, variants, prices
- ✅ **Automatic Retry System**: Failed stores saved for easy retry
- ✅ **S3 Export**: Direct cloud storage integration
- ✅ **Store Filtering**: Automatic Shopify store identification
- ✅ **Detailed Reporting**: JSON reports with full scrape analytics
- ✅ **Price Extraction**: Min/max pricing across variants
- ✅ **No Zyte API**: Cost-effective, no external API dependencies

## 🛠️ Development

### Adding/Removing Stores
1. **Edit** `data/master_store_list.txt` (add/remove domains)
2. **⚠️ IMPORTANT**: Run `python store_filter/filter_shopify_stores.py`
3. **Update spider**: Run `python update_spider_stores.py`
4. **Deploy**: Run `shub deploy`

### Custom Settings
Modify `shopify_scraper/settings.py` for:
- **Rate Limiting**: `DOWNLOAD_DELAY`, `CONCURRENT_REQUESTS`
- **Memory Management**: `MEMUSAGE_LIMIT_MB`, `MEMUSAGE_WARNING_MB`
- **User Agents**: `USER_AGENT_LIST`
- **Retry Logic**: `RETRY_TIMES`, `RETRY_DELAY_MIN/MAX`
- **S3 Export**: `FEEDS` configuration

### Workflow
```
1. Edit master_store_list.txt
2. Run filter_shopify_stores.py  ← CRITICAL STEP
3. Run update_spider_stores.py   ← NEW STEP
4. Test with single store
5. Deploy to ScrapyCloud
6. Run full production scrape
```

## 🔧 ScrapyCloud Deployment

### Hardcoded Stores Approach
The spider uses **hardcoded stores** for ScrapyCloud deployment to avoid file path issues:

- **✅ Reliable**: No file dependencies on ScrapyCloud
- **✅ Automatic**: All 52 stores loaded automatically
- **✅ No Arguments**: Run spider with no arguments needed
- **✅ Easy Updates**: Use `update_spider_stores.py` to sync changes

### Helper Scripts
```bash
# Generate ScrapyCloud arguments (alternative approach)
python generate_scrapycloud_args.py

# Update spider with latest stores
python update_spider_stores.py
```

## 📝 Technical Notes

- **API**: Uses Shopify's public JSON API (`/products.json`)
- **No Browser**: No browser automation required
- **Pagination**: Handles pagination automatically (250 products/page)
- **Images**: Extracts up to 4 product images per item
- **Rate Limiting**: Custom middleware prevents 429 errors
- **Memory**: Monitors usage to prevent crashes
- **Reporting**: Generates comprehensive JSON reports
- **ScrapyCloud**: Hardcoded stores for reliable cloud deployment
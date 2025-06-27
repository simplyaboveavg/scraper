# Shopify Scraper

A robust, scalable Scrapy spider for scraping product data from multiple Shopify stores while respecting rate limits.

## Features

- **Multi-store support**: Scrape hundreds of Shopify stores in a single run
- **Batch processing**: Process stores in configurable batches to avoid overwhelming servers
- **Rate limiting**: Intelligent delays between requests to avoid getting blocked
- **Progress tracking**: Resume scraping from where you left off if interrupted
- **Configurable**: Adjust batch sizes, delays, and other parameters via command line
- **Robust error handling**: Automatically retry failed requests with exponential backoff
- **Non-blocking**: Uses Twisted's asynchronous architecture for efficient scraping

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/shopify_scraper.git
cd shopify_scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

To run the scraper with default settings:

```bash
scrapy crawl shopify_multi
```

This will load store URLs from `store_filter/shopify_stores.json` and process them in batches of 10.

### Command Line Options

The scraper supports several command line options:

- `store_url`: Scrape a single store
- `batch_size`: Number of stores to process in each batch (default: 10)
- `resume`: Resume scraping from where you left off
- `stores_file`: Path to a JSON file containing store URLs

Examples:

```bash
# Scrape a single store
scrapy crawl shopify_multi -a store_url=https://example.com

# Process stores in batches of 5
scrapy crawl shopify_multi -a batch_size=5

# Resume a previously interrupted scrape
scrapy crawl shopify_multi -a resume=true

# Use a custom stores file
scrapy crawl shopify_multi -a stores_file=my_stores.json

# Combine options
scrapy crawl shopify_multi -a batch_size=20 -a resume=true -a stores_file=my_stores.json
```

### Store List Format

The scraper can load store URLs from a JSON file in either of these formats:

1. Array format:
```json
[
  "store1.com",
  "store2.com",
  "store3.com"
]
```

2. Object format:
```json
{
  "stores": [
    "store1.com",
    "store2.com",
    "store3.com"
  ]
}
```

URLs can be provided with or without the `https://` prefix. The scraper will automatically add it if missing.

## Handling Rate Limits

The scraper implements several strategies to avoid hitting rate limits:

1. **Batch processing**: Stores are processed in small batches (default: 10)
2. **Inter-store delays**: Waits 60-120 seconds between stores
3. **Inter-batch delays**: Waits 5-10 minutes between batches
4. **Page delays**: Waits 2-5 seconds between pages of the same store
5. **Exponential backoff**: Automatically increases wait time after encountering errors
6. **Random user agents**: Rotates through a list of realistic user agents
7. **Custom retry middleware**: Intelligently handles rate limit responses

## ScrapyCloud Deployment

To deploy to ScrapyCloud:

1. Make sure you have the Scrapinghub command line tool:
```bash
pip install shub
```

2. Login to your ScrapyCloud account:
```bash
shub login
```

3. Deploy the project:
```bash
shub deploy
```

4. Run the spider on ScrapyCloud with custom settings:
```bash
shub schedule shopify_multi -a batch_size=20 -a resume=true
```

## Filtering Shopify Stores

The repository includes a utility script to filter a list of domains and identify which ones are Shopify stores:

```bash
cd store_filter
python filter_shopify_stores.py
```

This will read domains from `master_store_list.txt` and output two files:
- `shopify_stores.json`: Contains domains that are Shopify stores
- `non_shopify_stores.json`: Contains domains that are not Shopify stores

## Output

The scraper outputs product data in JSON Lines format. Each line contains a complete product record with the following fields:

- `store`: The store URL
- `id`: Product ID
- `title`: Product title
- `handle`: Product handle (URL slug)
- `vendor`: Product vendor
- `product_type`: Product type/category
- `tags`: Product tags
- `variants`: Array of product variants (sizes, colors, etc.)
- `images`: Array of product images
- `body_html`: Product description HTML

## Troubleshooting

### Rate Limiting

If you're still experiencing rate limiting issues:

1. Increase the delay parameters in the spider:
```python
INTER_STORE_DELAY_MIN = 120  # Increase from 60 to 120
INTER_STORE_DELAY_MAX = 240  # Increase from 120 to 240
INTER_BATCH_DELAY_MIN = 600  # Increase from 300 to 600
INTER_BATCH_DELAY_MAX = 1200  # Increase from 600 to 1200
```

2. Decrease the batch size:
```bash
scrapy crawl shopify_multi -a batch_size=5
```

3. Consider using proxies by adding them to the `ROTATING_PROXIES_LIST` in `settings.py`

### Memory Issues

If you encounter memory issues with large datasets:

1. Enable item pipelines to process and export items immediately
2. Reduce the batch size
3. Use the `JOBDIR` setting to enable disk-based request queues:
```bash
scrapy crawl shopify_multi -s JOBDIR=crawls/shopify_multi
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

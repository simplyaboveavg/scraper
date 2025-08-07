# ScrapyCloud Deployment Guide

## 🚀 Ready for ScrapyCloud Deployment

The Shopify scraper has been configured for ScrapyCloud deployment with the following optimizations:

### ✅ **ScrapyCloud Compatibility Features:**

1. **Reactor Configuration**: 
   - TWISTED_REACTOR setting is commented out to use ScrapyCloud's default EPollReactor
   - No manual reactor installation in spider code

2. **Environment Detection**:
   - Uses `SHUB_JOBKEY` environment variable to detect ScrapyCloud environment
   - Automatically adapts configuration for cloud vs local execution

3. **Updated Stack**: 
   - Uses `scrapy:2.11-py39` stack for better Zyte API compatibility
   - All required dependencies in `requirements.txt`

### 📋 **Deployment Steps:**

1. **Deploy to ScrapyCloud:**
   ```bash
   cd shopify_scraper
   shub deploy
   ```

2. **Set Environment Variables in ScrapyCloud:**
   - `ZYTE_API_KEY`: Your Zyte API key
   - `AWS_ACCESS_KEY_ID`: For S3 uploads
   - `AWS_SECRET_ACCESS_KEY`: For S3 uploads

3. **Run the Spider:**
   ```bash
   # Run with all stores from shopify_stores.json
   shub schedule shopify_multi

   # Run with specific store
   shub schedule shopify_multi -a store_url=https://americantall.com

   # Run with limited pages for testing
   shub schedule shopify_multi -s CLOSESPIDER_PAGECOUNT=2
   ```

### 🔧 **Configuration Files:**

- **`scrapinghub.yml`**: Project configuration with updated stack
- **`requirements.txt`**: All dependencies including `scrapy-zyte-api>=0.13.0`
- **`settings.py`**: ScrapyCloud-compatible settings with Zyte API integration

### 📊 **Data Output:**

- **S3 Bucket**: `s3://simplyaboveaverage-scrapy/raw-shopify/`
- **Format**: JSON Lines with enhanced image extraction
- **Fields**: Includes `image_url`, `image_url_2`, `image_url_3`, `image_url_4`

### 🏪 **Store Management:**

1. **Update Master List**: Edit `store_filter/master_store_list.txt`
2. **Run Filter**: `python3 store_filter/filter_shopify_stores.py`
3. **Copy Results**: `cp store_filter/shopify_stores.json shopify_scraper/shopify_stores.json`
4. **Deploy**: `shub deploy`

### 🔍 **Monitoring:**

- Check ScrapyCloud dashboard for job status
- Monitor S3 bucket for output files
- Review logs for any Zyte API issues

### 🚨 **Troubleshooting:**

- **Reactor Errors**: Ensure TWISTED_REACTOR is commented out
- **Zyte API Issues**: Verify API key is set in environment variables
- **S3 Upload Failures**: Check AWS credentials in ScrapyCloud settings

The scraper is now fully compatible with ScrapyCloud's infrastructure and ready for production deployment!

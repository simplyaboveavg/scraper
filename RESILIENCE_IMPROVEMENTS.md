# Shopify Spider Resilience and Rate Limiting Improvements

## Overview
This document outlines the improvements made to make the Shopify spider more resilient per-store and better at handling rate limiting from both Zyte and Shopify.

## Key Improvements

### 1. Per-Store Resilience

#### Store Failure Tracking
- **Failed Stores Set**: Tracks stores that have failed too many times and should be skipped
- **Store Failures Counter**: Counts failures per store to implement progressive penalties
- **Store Start Times**: Tracks when each store started to implement timeouts

#### Resilience Settings
```python
MAX_STORE_FAILURES = 3      # Max consecutive failures before skipping store
STORE_TIMEOUT = 300         # Max time to spend on a single store (seconds)
MAX_PAGES_PER_STORE = 100   # Safety limit to prevent infinite loops
```

#### Store Isolation
- Individual store failures no longer stall the entire batch
- Failed stores are automatically skipped in subsequent processing
- Store-specific error handling with detailed logging
- Automatic cleanup of tracking data for completed stores

### 2. Enhanced Rate Limiting

#### Scrapy Settings Improvements
- **Reduced Concurrency**: `CONCURRENT_REQUESTS = 2` (down from 4)
- **Conservative Domain Limits**: `CONCURRENT_REQUESTS_PER_DOMAIN = 1`
- **Enhanced AutoThrottle**: 
  - Start delay: 15s (up from 10s)
  - Max delay: 180s (up from 120s)
  - Target concurrency: 0.3 (down from 0.5)
- **Increased Base Delay**: `DOWNLOAD_DELAY = 2.0s` (up from 1.0s)

#### Middleware Rate Limiting
- **Sophisticated Delay System**: Variable delays based on probability distribution
  - 60% of requests: 2-6 seconds
  - 25% of requests: 6-12 seconds  
  - 15% of requests: 12-20 seconds
- **Failure-Based Backoff**: Extra delays for stores with previous failures
- **Store-Aware Processing**: Middleware can skip requests for failed stores

### 3. Error Handling Improvements

#### HTTP Status Code Handling
- **429 (Rate Limited)**: Automatic detection and progressive backoff
- **403 (Forbidden)**: Tracked as store failure with appropriate messaging
- **404 (Not Found)**: Identified as potentially non-Shopify stores
- **5xx Errors**: Handled with exponential backoff

#### Exception Handling
- **JSON Parsing Errors**: Graceful handling of malformed responses
- **Connection Errors**: Automatic retry with exponential backoff
- **Timeout Handling**: Per-store timeout limits to prevent hanging

### 4. Progressive Failure Management

#### Store-Level Failures
1. **First Failure**: Log warning, continue with normal processing
2. **Second Failure**: Add extra delay, continue processing
3. **Third Failure**: Mark store as failed, skip in future processing

#### Request-Level Retries
- Reduced per-page retries from 5 to 3 to fail faster
- Exponential backoff with jitter to avoid thundering herd
- Smart header rotation to appear more browser-like

### 5. Monitoring and Logging

#### Enhanced Logging
- Store-specific log prefixes for easy filtering
- Detailed failure reasons and counts
- Progress tracking with completion status
- Heartbeat logging for long delays

#### Progress Persistence
- Automatic saving of completed stores
- Resume capability to continue from interruptions
- Failure state persistence across restarts

## Usage Examples

### Running with Custom Settings
```bash
# Run with smaller batch size for testing
scrapy crawl shopify_multi -s BATCH_SIZE=5

# Run with custom delays
scrapy crawl shopify_multi -s DOWNLOAD_DELAY=3.0

# Resume interrupted scraping
scrapy crawl shopify_multi -a resume=true
```

### Monitoring Store Failures
The spider automatically logs store failures:
```
[store.com] Store failure #1: HTTP 429 (Rate Limited)
[store.com] Store failure #2: Data parsing error on page 3
[store.com] Store marked as failed after 3 failures
```

### Progress Tracking
Progress is automatically saved to `scraping_progress.json`:
```json
{
  "completed_stores": ["store1.com", "store2.com"],
  "timestamp": 1704067200
}
```

## Benefits

### Reliability
- **No Single Point of Failure**: One problematic store won't stop the entire run
- **Automatic Recovery**: Failed stores are skipped, allowing progress to continue
- **Timeout Protection**: Prevents hanging on unresponsive stores

### Rate Limit Compliance
- **Adaptive Delays**: Longer delays for previously rate-limited stores
- **Conservative Defaults**: Settings optimized to stay under typical rate limits
- **Exponential Backoff**: Progressive delays reduce server load

### Operational Efficiency
- **Resume Capability**: Can restart from interruptions without losing progress
- **Detailed Logging**: Easy to identify and debug problematic stores
- **Batch Processing**: Efficient handling of large store lists

## Configuration Options

### Environment Variables
```bash
DOWNLOAD_DELAY=2.0          # Base delay between requests
LOG_LEVEL=INFO              # Logging verbosity
ZYTE_API_KEY=your_key       # Enable Zyte API integration
```

### Spider Arguments
```bash
-a batch_size=10            # Stores per batch
-a resume=true              # Resume from previous run
-a stores_file=stores.json  # Custom store list file
```

## Monitoring Recommendations

1. **Watch for Rate Limiting**: Monitor logs for 429 responses
2. **Track Store Failures**: Review failed stores for patterns
3. **Monitor Progress**: Check `scraping_progress.json` for completion status
4. **Resource Usage**: Monitor CPU/memory during long delays

## Smart Zyte Browser Mode Switching

### Two-Phase Processing
The spider now implements a cost-effective two-phase approach:

1. **Phase 1 - Lightweight Mode**: Process all stores using standard HTTP requests
2. **Phase 2 - Browser Mode Retry**: Retry failed stores using full browser rendering

### How It Works
- **Initial Processing**: All stores are processed with lightweight requests (no browser rendering)
- **Failure Tracking**: Stores that fail are automatically tracked and saved
- **Automatic Transition**: When Phase 1 completes, failed stores are automatically retried with browser mode
- **Cost Optimization**: Browser rendering is only used when necessary, reducing Zyte API costs

### Browser Mode Features
- **Full JavaScript Rendering**: Handles stores with heavy client-side protection
- **Geolocation Support**: Requests appear to come from the US
- **Automatic Switching**: No manual intervention required
- **Progress Tracking**: Separate tracking for each phase

### Configuration
```python
# Enable/disable browser mode retry phase
BROWSER_MODE_RETRY = True

# Files for tracking progress
PROGRESS_FILE = 'scraping_progress.json'
FAILED_STORES_FILE = 'failed_stores.json'
```

### Usage Examples
```bash
# Normal run (automatic two-phase processing)
scrapy crawl shopify_multi

# Check failed stores that will be retried
cat failed_stores.json

# Monitor phase transitions in logs
tail -f scrapy.log | grep "PHASE"
```

### Cost Benefits
- **Reduced API Costs**: Browser mode only used for problematic stores (~10-20% of total)
- **Improved Success Rate**: Failed stores get a second chance with full rendering
- **Automatic Optimization**: No manual intervention needed to identify which stores need browser mode

## Future Enhancements

1. **Dynamic Rate Limiting**: Adjust delays based on response times
2. **Store Health Scoring**: Prioritize reliable stores
3. **Distributed Processing**: Split store lists across multiple instances
4. **Real-time Monitoring**: Dashboard for tracking scraping progress
5. **Hardcoded Problem Store Lists**: Pre-configure known difficult stores to start with browser mode

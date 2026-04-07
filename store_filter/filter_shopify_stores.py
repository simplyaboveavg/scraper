#!/usr/bin/env python3
"""
Filter master store list into Shopify vs non-Shopify.

Usage (from project root):
    python store_filter/filter_shopify_stores.py

Input:  data/master_store_list.txt  (one domain per line)
Output: shopify_scraper/data/shopify_stores.json   (spider reads this directly)
        shopify_scraper/data/non_shopify_stores.json
"""

import requests
import json
import time
import os

# All paths relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_LIST = os.path.join(PROJECT_ROOT, "data", "master_store_list.txt")
# Output goes INTO the package so the spider + ScrapyCloud can find it
PACKAGE_DATA = os.path.join(PROJECT_ROOT, "shopify_scraper", "data")
SHOPIFY_OUT = os.path.join(PACKAGE_DATA, "shopify_stores.json")
NON_SHOPIFY_OUT = os.path.join(PACKAGE_DATA, "non_shopify_stores.json")
# Also keep a copy in data/ for easy reference
DATA_SHOPIFY_OUT = os.path.join(PROJECT_ROOT, "data", "shopify_stores.json")
DATA_NON_SHOPIFY_OUT = os.path.join(PROJECT_ROOT, "data", "non_shopify_stores.json")


def is_shopify(domain):
    try:
        url = f"https://{domain}/products.json?limit=1"
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})

        # Check for Shopify-specific headers or valid product structure
        is_json = response.headers.get('Content-Type', '').startswith('application/json')
        has_shopify_header = any(h.lower().startswith("x-shopify") for h in response.headers)

        return (response.status_code == 200 and is_json) or has_shopify_header

    except requests.RequestException:
        return False


def filter_domains():
    if not os.path.exists(MASTER_LIST):
        print(f"Error: {MASTER_LIST} not found")
        return

    with open(MASTER_LIST, 'r') as f:
        domains = [line.strip() for line in f if line.strip()]

    # Load existing shopify stores to avoid re-checking known ones
    existing_shopify = set()
    if os.path.exists(SHOPIFY_OUT):
        with open(SHOPIFY_OUT, 'r') as f:
            existing_shopify = set(json.load(f).get('stores', []))

    shopify = []
    non_shopify = []

    for i, domain in enumerate(domains):
        if domain in existing_shopify:
            shopify.append(domain)
            print(f"[{i+1}/{len(domains)}] {domain} — already verified ✅")
            continue

        print(f"[{i+1}/{len(domains)}] Checking {domain}...", end=" ")
        if is_shopify(domain):
            shopify.append(domain)
            print("✅ Shopify")
        else:
            non_shopify.append(domain)
            print("❌ NOT Shopify")

        time.sleep(1)  # Rate limit between checks

    # Ensure output directory exists
    os.makedirs(PACKAGE_DATA, exist_ok=True)

    # Write to package data (spider reads this)
    for path in [SHOPIFY_OUT, DATA_SHOPIFY_OUT]:
        with open(path, 'w') as f:
            json.dump({"stores": shopify}, f, indent=2)

    for path in [NON_SHOPIFY_OUT, DATA_NON_SHOPIFY_OUT]:
        with open(path, 'w') as f:
            json.dump({"stores": non_shopify}, f, indent=2)

    print(f"\nDone: ✅ {len(shopify)} Shopify | ❌ {len(non_shopify)} Non-Shopify")
    print(f"Spider will read: {SHOPIFY_OUT}")


if __name__ == "__main__":
    filter_domains()

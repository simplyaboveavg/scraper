#!/usr/bin/env python3
"""
Generate ScrapyCloud arguments for the shopify_multi spider.
This script reads the shopify_stores.json file and generates the JSON string
needed to pass all stores to ScrapyCloud.
"""

import json
import sys
import os

def generate_scrapycloud_args():
    """Generate the stores_json argument for ScrapyCloud"""
    
    # Read the shopify stores file
    stores_file = 'data/shopify_stores.json'
    
    if not os.path.exists(stores_file):
        print(f"❌ Error: {stores_file} not found!")
        print("Run: python store_filter/filter_shopify_stores.py first")
        return None
    
    try:
        with open(stores_file, 'r') as f:
            data = json.load(f)
        
        # Convert to JSON string
        json_string = json.dumps(data)
        
        print("✅ ScrapyCloud Arguments Generated!")
        print("=" * 60)
        print("Copy this JSON string to use in ScrapyCloud:")
        print("=" * 60)
        print(json_string)
        print("=" * 60)
        print(f"📊 Total stores: {len(data.get('stores', []))}")
        print("=" * 60)
        print("🔧 How to use in ScrapyCloud:")
        print("1. Go to: https://app.zyte.com/p/804888/")
        print("2. Click 'Run Spider'")
        print("3. Select 'shopify_multi'")
        print("4. In 'Arguments' field, add:")
        print(f"   stores_json='{json_string}'")
        print("5. Click 'Run'")
        print("=" * 60)
        
        return json_string
        
    except Exception as e:
        print(f"❌ Error reading {stores_file}: {e}")
        return None

if __name__ == "__main__":
    generate_scrapycloud_args()

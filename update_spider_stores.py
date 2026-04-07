#!/usr/bin/env python3
"""
Update the hardcoded stores in the spider from data/shopify_stores.json
This script reads the filtered Shopify stores and updates the spider code.
"""

import json
import re
import os

def update_spider_stores():
    """Update the hardcoded stores in the spider"""
    
    # Read the shopify stores file
    stores_file = 'data/shopify_stores.json'
    spider_file = 'shopify_scraper/spiders/shopify_spider.py'
    
    if not os.path.exists(stores_file):
        print(f"❌ Error: {stores_file} not found!")
        print("Run: python store_filter/filter_shopify_stores.py first")
        return False
    
    try:
        # Load stores
        with open(stores_file, 'r') as f:
            data = json.load(f)
        
        stores = data.get('stores', [])
        if not stores:
            print("❌ Error: No stores found in shopify_stores.json")
            return False
        
        # Convert to https URLs
        https_stores = []
        for store in stores:
            store = store.rstrip('/')
            if not store.startswith(('http://', 'https://')):
                store = f'https://{store}'
            https_stores.append(store)
        
        # Read current spider file
        with open(spider_file, 'r') as f:
            spider_content = f.read()
        
        # Generate new stores list
        stores_list = "[\n"
        for i, store in enumerate(https_stores):
            stores_list += f"                '{store}'"
            if i < len(https_stores) - 1:
                stores_list += ","
            stores_list += "\n"
        stores_list += "            ]"
        
        # Replace the stores list in the spider
        pattern = r'# Hardcoded stores for ScrapyCloud.*?\]'
        replacement = f'# Hardcoded stores for ScrapyCloud (auto-generated from data/shopify_stores.json)\n            {stores_list}'
        
        new_content = re.sub(pattern, replacement, spider_content, flags=re.DOTALL)
        
        if new_content == spider_content:
            print("❌ Error: Could not find stores list to replace in spider file")
            return False
        
        # Write updated spider file
        with open(spider_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Spider stores updated successfully!")
        print(f"📊 Total stores: {len(https_stores)}")
        print(f"📝 Updated: {spider_file}")
        print("🚀 Next step: shub deploy")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    update_spider_stores()

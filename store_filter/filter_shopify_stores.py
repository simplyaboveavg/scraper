import requests
import json
import time

def is_shopify(domain):
    try:
        url = f"https://{domain}/products.json?limit=1"
        response = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})

        # Check for Shopify-specific headers or valid product structure
        is_json = response.headers.get('Content-Type', '').startswith('application/json')
        has_shopify_header = any(h.lower().startswith("x-shopify") for h in response.headers)

        return (response.status_code == 200 and is_json) or has_shopify_header

    except requests.RequestException:
        return False


def filter_domains(input_file, shopify_file, non_shopify_file):
    with open(input_file, 'r') as f:
        domains = [line.strip() for line in f if line.strip()]

    shopify = []
    non_shopify = []

    for i, domain in enumerate(domains):
        print(f"[{i+1}/{len(domains)}] Checking {domain}...")
        if is_shopify(domain):
            shopify.append(domain)
            print(f"✅ {domain} is Shopify")
        else:
            non_shopify.append(domain)
            print(f"❌ {domain} is NOT Shopify")

        time.sleep(1)  # Rate limit

    # Save results
    with open(shopify_file, 'w') as f:
        json.dump({"stores": shopify}, f, indent=2)

    with open(non_shopify_file, 'w') as f:
        json.dump({"stores": non_shopify}, f, indent=2)

    print(f"\nFinished. ✅ {len(shopify)} Shopify | ❌ {len(non_shopify)} Non-Shopify")


# ---- Run this script ----
if __name__ == "__main__":
    filter_domains(
        input_file="master_store_list.txt",
        shopify_file="shopify_stores.json",
        non_shopify_file="non_shopify_stores.json"
    )

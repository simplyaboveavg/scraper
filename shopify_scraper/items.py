# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ShopifyProductItem(scrapy.Item):
    store = scrapy.Field()
    id = scrapy.Field()
    title = scrapy.Field()
    handle = scrapy.Field()
    vendor = scrapy.Field()
    product_type = scrapy.Field()
    tags = scrapy.Field()
    variants = scrapy.Field()
    images = scrapy.Field()  # Keep original images array for compatibility
    body_html = scrapy.Field()
    product_url = scrapy.Field()
    
    # Individual image fields (up to 4 images)
    image_url = scrapy.Field()    # Primary image
    image_url_2 = scrapy.Field()  # Second image
    image_url_3 = scrapy.Field()  # Third image
    image_url_4 = scrapy.Field()  # Fourth image

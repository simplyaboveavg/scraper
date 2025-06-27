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
    images = scrapy.Field()
    body_html = scrapy.Field()
    product_url = scrapy.Field() 

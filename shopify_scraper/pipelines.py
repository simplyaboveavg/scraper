# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from scrapy.exporters import CsvItemExporter, JsonLinesItemExporter
import os
import json
import re
import time


class CleanTextMixin:
    """
    Mixin to clean text by replacing unusual line terminators with standard newlines.
    """
    
    def clean_text(self, text):
        """
        Clean text by replacing unusual line terminators with standard newlines.
        
        Args:
            text (str): The text to clean
            
        Returns:
            str: The cleaned text
        """
        if text is None:
            return None
            
        # Replace Line Separator (U+2028) and Paragraph Separator (U+2029) with standard newlines
        text = text.replace('\u2028', '\n').replace('\u2029', '\n')
        
        # Normalize all newlines to Unix style (LF)
        text = text.replace('\r\n', '\n')
        
        return text
    
    def clean_item(self, item):
        """
        Clean all string fields in an item to ensure no unusual line terminators.
        
        Args:
            item (dict): The item to clean
            
        Returns:
            dict: The cleaned item
        """
        for key, value in item.items():
            if isinstance(value, str):
                item[key] = self.clean_text(value)
            elif isinstance(value, (list, dict)):
                # For complex fields, convert to JSON and back to ensure all strings are cleaned
                json_str = json.dumps(value)
                json_str = self.clean_text(json_str)
                item[key] = json.loads(json_str)
        return item


class ShopifyScraperPipeline(CleanTextMixin):
    def __init__(self):
        self.exporters = {}
        self.files = {}

        # Create output folder if needed
        self.output_dir = 'store_exports'
        os.makedirs(self.output_dir, exist_ok=True)

    def open_spider(self, spider):
        pass  # Nothing needed here

    def close_spider(self, spider):
        # Close all open file handles
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for file in self.files.values():
            file.close()

    def _get_exporter_for_store(self, store_url):
        domain = store_url.replace('https://', '').replace('http://', '').replace('/', '')
        filename = os.path.join(self.output_dir, f'{domain}.csv')

        if domain not in self.exporters:
            f = open(filename, 'wb')
            exporter = CsvItemExporter(f)
            exporter.fields_to_export = [
                'id', 'title', 'handle', 'vendor', 'product_type', 'tags',
                'variants', 'images', 'body_html', 'product_url'
            ]
            exporter.start_exporting()

            self.files[domain] = f
            self.exporters[domain] = exporter

        return self.exporters[domain]

    def process_item(self, item, spider):
        # Clean the item to remove unusual line terminators
        cleaned_item = self.clean_item(item)
        
        store_url = cleaned_item.get('store')
        if not store_url:
            return cleaned_item  # Skip items without store info

        exporter = self._get_exporter_for_store(store_url)
        exporter.export_item(cleaned_item)
        return cleaned_item


class JsonLinesExportPipeline(CleanTextMixin):
    """
    Pipeline for exporting items as newline-delimited JSON records.
    """
    def __init__(self):
        self.exporters = {}
        self.files = {}

        # Create output folder if needed
        self.output_dir = 'json_exports'
        os.makedirs(self.output_dir, exist_ok=True)

    def open_spider(self, spider):
        # Create a single file for all items from this spider run using the same format as S3 export
        timestamp = time.strftime('%Y-%m-%dT%H-%M-%S')
        filename = os.path.join(self.output_dir, f'{spider.name}-{timestamp}.json')
        self.file = open(filename, 'wb')
        self.exporter = JsonLinesItemExporter(self.file, ensure_ascii=False)
        self.exporter.start_exporting()
        spider.logger.info(f"JsonLinesExportPipeline: Exporting to {filename}")

    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.file.close()
        spider.logger.info("JsonLinesExportPipeline: Export completed")

    def process_item(self, item, spider):
        # Clean the item to remove unusual line terminators
        cleaned_item = self.clean_item(item)
        self.exporter.export_item(cleaned_item)
        return cleaned_item

# Automatically created by: shub deploy

from setuptools import setup, find_packages

setup(
    name         = 'project',
    version      = '1.0',
    packages     = find_packages(),
    package_data = {
        'shopify_scraper': ['data/*.json'],
    },
    entry_points = {'scrapy': ['settings = shopify_scraper.settings']},
)

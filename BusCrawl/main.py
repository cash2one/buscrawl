# -*- coding: utf-8 -*-
import os
import sys

from scrapy import cmdline

path = os.path.dirname(__file__)
sys.path.append(os.path.join(path, ".."))
# cmdline.execute("scrapy crawl kuaiba -a province=北京".split())

cmdline.execute("scrapy crawl scqcp -a city=成都市".split())
# cmdline.execute("scrapy crawl bjky".split())

# cmdline.execute("scrapy crawl bus100 -a province_id=450000".split())
# cmdline.execute("scrapy crawl bus100 -a province_id=210000 -a city=沈阳市".split())

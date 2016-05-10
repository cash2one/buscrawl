# -*- coding: utf-8 -*-
import os
import sys

from scrapy import cmdline

path = os.path.dirname(__file__)
sys.path.append(os.path.join(path, ".."))
# cmdline.execute("scrapy crawl kuaiba -a province=北京".split())

# cmdline.execute("scrapy crawl scqcp -a city=德阳市".split())
# cmdline.execute("scrapy crawl hebky -a city=唐山".split())
cmdline.execute("scrapy crawl hebky".split())
# cmdline.execute("scrapy crawl bus100 -a province_id=450000".split())
# cmdline.execute("scrapy crawl nmghy".split())
# cmdline.execute("scrapy crawl ctrip -a province=北京".split())
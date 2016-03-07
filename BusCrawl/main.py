import os
import sys

from scrapy import cmdline

path = os.path.dirname(__file__)
sys.path.append(os.path.join(path, ".."))
cmdline.execute("scrapy crawl kuaiba".split())

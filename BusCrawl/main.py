# -*- coding: utf-8 -*-
import os
import sys

from scrapy import cmdline

path = os.path.dirname(__file__)
sys.path.append(os.path.join(path, ".."))
# cmdline.execute("scrapy crawl kuaiba -a province=北京".split())

cmdline.execute("scrapy crawl scqcp -a city=德阳市".split())
# cmdline.execute("scrapy crawl hebky -a city=唐山".split())
# cmdline.execute("scrapy crawl hebky".split())
# cmdline.execute("scrapy crawl bus100 -a province_id=450000".split())
# cmdline.execute("scrapy crawl xintuyun -a city=沈阳市".split())
# cmdline.execute("scrapy crawl ctrip -a province=北京".split())
#cmdline.execute("scrapy crawl bus365 -a city=哈尔滨市,齐齐哈尔,鸡西市,鹤岗市,双鸭山市,大庆市,伊春市,佳木斯市,七台河市,牡丹江市,黑河市".split())
#cmdline.execute("scrapy crawl bus365 -a city=长春市,吉林市,四平市,辽源市,通化市,白山市,松原市,白城市,图们市,敦化市,珲春市,龙井市,和龙市".split())
# cmdline.execute("scrapy crawl bus365 -a city=哈尔滨市".split())
# cmdline.execute("scrapy crawl szky".split())
# cmdline.execute("scrapy crawl dgky -a city=长安客运站".split())
# cmdline.execute("scrapy crawl gdsw -a city=东莞".split())
# cmdline.execute("scrapy crawl e8s".split())
# cmdline.execute("scrapy crawl wmcx -a province=安徽".split())

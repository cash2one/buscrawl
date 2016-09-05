# -*- coding: utf-8 -*-
import os
import sys

from scrapy import cmdline

path = os.path.dirname(__file__)
sys.path.append(os.path.join(path, ".."))
# cmdline.execute("scrapy crawl kuaiba -a province=北京".split())

# cmdline.execute("scrapy crawl scqcp -a city=宜宾市".split())
# cmdline.execute("scrapy crawl hebky -a city=唐山".split())
# cmdline.execute("scrapy crawl hebky".split())
# cmdline.execute("scrapy crawl bus100 -a province_id=450000".split())
# cmdline.execute("scrapy crawl xintuyun -a city=沈阳市".split())
# cmdline.execute("scrapy crawl ctrip -a province=北京".split())
#cmdline.execute("scrapy crawl bus365 -a city=哈尔滨市,齐齐哈尔,鸡西市,鹤岗市,双鸭山市,大庆市,伊春市,佳木斯市,七台河市,牡丹江市,黑河市".split())
#cmdline.execute("scrapy crawl bus365 -a city=长春市,吉林市,四平市,辽源市,通化市,白山市,松原市,白城市,图们市,敦化市,珲春市,龙井市,和龙市".split())
# cmdline.execute("scrapy crawl bus365 -a city=哈尔滨市".split())
# cmdline.execute("scrapy crawl szky".split())
# cmdline.execute("scrapy crawl dgky -a city=松山湖汽车客运站".split())
# cmdline.execute("scrapy crawl gdsw -a city=东莞".split())
# cmdline.execute("scrapy crawl e8s".split())
# cmdline.execute("scrapy crawl wmcx -a province=安徽".split())
# cmdline.execute("scrapy crawl fjky -a city=南平市,宁德市,福安市,福鼎市,古田县,光泽县,建阳市,建瓯市,明溪县,屏南县,浦城县,邵武市,寿宁县,顺昌县,松溪县,武夷山市,霞浦县,政和县,周宁县,柘荣县".split())
# cmdline.execute("scrapy crawl gzqcp -a city=贵阳,安顺,毕节市,凯里市".split())
# cmdline.execute("scrapy crawl bus365 -a city=天津市".split())
# cmdline.execute("scrapy crawl hebky".split())
# cmdline.execute("scrapy crawl qdky".split())
cmdline.execute("scrapy crawl hainky".split())
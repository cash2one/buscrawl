# -*- coding: utf-8 -*-
import scrapy
import json
import urllib

from datetime import datetime as dte
from pypinyin import lazy_pinyin
from BusCrawl.items.ctrip import StartItem, TargetItem, LineItem
from BusCrawl.utils.tool import md5

class ScqcpSpider(scrapy.Spider):
    name = "ctrip"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipelines.scqcp.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middlewares.common.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middlewares.common.ProxyMiddleware': 410,
            'BusCrawl.middlewares.ctrip.HeaderMiddleware': 410,
        }
    }
    base_url = "http://m.ctrip.com/restapi/busphp/app/index.php"

    def start_requests(self):
        # 这是个pc网页页面
        headers={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) \
                Chrome/47.0.2526.106 Safari/537.36"}
        web_page = "http://qiche.tieyou.com/index.php?param=/ajax/cityList"
        return [scrapy.Request(web_page, headers=headers, callback=self.parse_start_city)]

    def parse_start_city(self, response):
        res = json.loads(response.body[1:-1])
        params = dict(
            param="/api/home",
            method="product.getToCityList",
            ref="ctrip.h5",
            partner="ctrip.app",
            clientType="Android--hybrid",
            vendor="",
            fromCity="",
            contentType="json",
        )
        for pro in res['hotFromCity']['province']:
            province = pro["province_name"]
            if not province in ['四川']:
                continue
            self.logger.info("start province: %s" % province)
            for ci in pro["citys"]:
                pys = lazy_pinyin(unicode(ci))
                d = {
                    hash_key: md5("%s-%s-%s" % (province, ci, "ctrip")),
                    "province": province,
                    "name": ci,
                    "pinyin": "".join(pys),
                    "short_pinyin": "".join(map(lambda w:w[0], pys)),
                }
                yield StartItem(**d)
                params.update(fromCity=ci)
                url = "%s?%s" % (self.base_url, urllib.urlencode(params))
                yield scrapy.Request(url, callback=self.parse_target_city, meta={"start": d})

    def parse_target_city(self, response):
        res = json.loads(response.body)
        if int(res["code"]) != 1:
            self.logger.error("parse_target_city: Unexpected return, %s" % str(res))
            return

        for tar in res["return"]:
            d = {
                "name": tar["name"],
                "pinyin": tar["pinyin"],
                "short_pinyin": tar["shortPinyin"],
            }

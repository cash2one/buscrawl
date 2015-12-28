# -*- coding: utf-8 -*-
import scrapy
import json
import urllib
import datetime

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
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) \
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
            if province not in ['四川']:
                continue
            self.logger.info("start province: %s" % province)
            for ci in pro["citys"]:
                pys = lazy_pinyin(unicode(ci))
                d = {
                    "hash_key": md5("%s-%s-%s" % (province, ci, "ctrip")),
                    "province": province,
                    "name": ci,
                    "pinyin": "".join(pys),
                    "short_pinyin": "".join(map(lambda w: w[0], pys)),
                }
                params.update(fromCity=ci)
                url = "%s?%s" % (self.base_url, urllib.urlencode(params))
                yield scrapy.Request(url, callback=self.parse_target_city, meta={"start": d})

    def parse_target_city(self, response):
        res = json.loads(response.body)
        if int(res["code"]) != 1:
            self.logger.error("parse_target_city: Unexpected return, %s" % str(res))
            return

        start = response.meta["start"]
        for tar in res["return"]:
            d = {
                "name": tar["name"],
                "pinyin": tar["pinyin"],
                "short_pinyin": tar["shortPinyin"],
            }

            # 预售期10天
            today = datetime.date.today()
            for i in range(0, 10):
                sdate = str(today+datetime.timedelta(days=i))
                params = dict(
                    param="/api/home",
                    method="product.getBusList",
                    v="1.0",
                    ref="ctrip.h5",
                    partner="ctrip.app",
                    clientType="Android--hybrid",
                    fromCity=start["name"],
                    toCity=d["name"],
                    fromDate=sdate,
                    contentType="json",
                )
                url = "%s?%s" % (self.base_url, urllib.urlencode(params))
                yield scrapy.Request(url, callback=self.parse_line, meta={"start": start, "end": d})

    def parse_line(self, response):
        "解析班车"
        res = json.loads(response.body)
        if int(res["code"]) != 1:
            self.logger.error("parse_line: Unexpected return, %s" % str(res))
            return
        start = response.meta["start"]
        end = response.meta["end"]
        for d in res["return"]:
            from_station = unicode(d["fromStationName"])
            to_station = unicode(d["toStationName"])
            attrs = dict(
                s_province = start["province_name"],
                s_city_name = d["fromCityName"],
                s_city_pinyin = start["pinyin"],
                s_city_short_pinyin = start["short_pinyin"],
                s_sta_name = from_station,
                s_sta_pinyin = "".join(lazy_pinyin(from_station)),
                s_sta_short_pinyin = "".join(map(lambda w: w[0], lazy_pinyin(from_station))),
                d_city_name = d["toCityName"],
                d_city_pinyin = end["pinyin"],
                d_city_short_pinyin = end["short_pinyin"],
                d_sta_name = to_station,
                d_sta_pinyin = "".join(lazy_pinyin(to_station)),
                d_sta_short_pinyin = "".join(map(lambda w: w[0], lazy_pinyin(to_station))),
                line_id = md5("%s-%s-%s-%s" % ()),
                drv_date = scrapy.Field()
                drv_time = scrapy.Field()
                drv_datetime = scrapy.Field()
                distance = scrapy.Field()
                vehicle_type = scrapy.Field()
                seat_type = scrapy.Field()
                bus_num = scrapy.Field()
                full_price = scrapy.Field(serializer=float)
                half_price = scrapy.Field(serializer=float)
                fee = scrapy.Field(serializer=float)
                crawl_datetime = scrapy.Field()
                extra_info = scrapy.Field()
                left_tickets = scrapy.Field(serializer=int)
            )
            d["city_id"] = start["city_id"]
            d["city"] = start["city_name"]
            d["create_datetime"] = datetime.datetime.now()
            d["line_id"] = md5("%s-%s-%s-%s" % (d["carry_sta_id"], d["carry_sta_name"], d["stop_name"], d["drv_date_time"]))
            yield LineItem(**d)

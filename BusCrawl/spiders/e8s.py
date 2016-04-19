#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urlparse
from lxml import etree
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis
from scrapy.conf import settings
from pymongo import MongoClient


class E8sSpider(SpiderBase):
    name = "e8s"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.E8sProxyMiddleware': 410,
#             'BusCrawl.middleware.BjkyHeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 1,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def is_end_city(self, start, end):
        db_config = settings.get("MONGODB_CONFIG")
        client = MongoClient(db_config["url"])
        db = client[db_config["db"]]
        s_sta_name = start['s_sta_name']
        result = db.line.distinct('d_city_name', {'crawl_source': 'ctrip', 's_sta_name':s_sta_name})
        if end['stopName'] not in result:
            return 0
        else:
            return 1

    def start_requests(self):
        url = "http://m.e8s.com.cn/bwfpublicservice/endStation.action"
        return [scrapy.FormRequest(url, formdata={'jianPin': ''}, callback=self.parse_target_city)]

    def parse_target_city(self, response):
        "解析目的地城市"
        res = json.loads(response.body)
        print res
        if int(res["flag"]) != 1:
            self.logger.error("parse_target_city: Unexpected return, %s" % str(res))
            return
        start = {
                 "city_name": "北京",
                 "s_sta_name": "八王坟客运站"
                 }
        url = "http://m.e8s.com.cn/bwfpublicservice/stationGetSchPlan.action"
        for d in res["detail"]['list']:
            if not self.is_end_city(start, d):
                continue
            today = datetime.date.today()
            for i in range(1, 2):
                sdate = str(today+datetime.timedelta(days=i))
#                 if self.has_done(start["city_name"], d["stopName"], sdate):
#                     #self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
#                     continue
                fd = {
                    "drvDate": sdate,
                    "rowNum": "10",
                    "page": "1",
                    "stopId": str(d['stopId']),#"131000",#
                    "carryStaId": "-1"
                }
                yield scrapy.FormRequest(url,
                                         formdata=fd,
                                         callback=self.parse_line,
                                         meta={"start": start, "end": d, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        print end
        sdate = response.meta["sdate"]
        print response.body
        res = json.loads(response.body)
#         self.mark_done(start["city_name"], end["stopName"], sdate)
        res = res['detail']
        print res
        for d in res:
            if int(d['seatAmount']) == 0:
                continue
            if d['carrStaName'] != u"八王坟":
                continue
            attrs = dict(
                s_province = '北京',
                s_city_name = "北京",
                s_city_id = '',
                s_city_code= get_pinyin_first_litter(u"北京"),
                s_sta_name= d["carrStaName"],
                s_sta_id = d["carryStaId"],
                d_city_name = end['stopName'],
                d_city_code= get_pinyin_first_litter(end['stopName']),
                d_city_id = end['stopId'],
                d_sta_name = d["endstaName"],
                d_sta_id = '',
                drv_date = sdate,
                drv_time = d['drvTime'],
                drv_datetime = dte.strptime("%s %s" % (sdate, d['drvTime']), "%Y-%m-%d %H:%M"),
                distance = "0",
                vehicle_type = "",
                seat_type = "",
                bus_num = d['scheduleId'],
                full_price = float(d['fullPrice']),
                half_price = float(d['fullPrice'])/2,
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {},
                left_tickets = int(d['seatAmount']),
                crawl_source = "e8s",
                shift_id='',
            )
            yield LineItem(**attrs)



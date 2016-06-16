#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis
from scrapy.conf import settings
from pymongo import MongoClient


class SzkySpider(SpiderBase):
    name = "szky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.SzkyHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
       "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        start_url = "http://www.vchepiao.cn/mb/base/bus/queryNewSKY"
        station_dict = {
                        "B1K003": '福田汽车客运站',
                        "B1K002": "深圳湾客运服务点",
                        "B1K004": "南山汽车客运站",
                        "B1K005": "盐田汽车客运站",
                        "B1K006": "东湖汽车客运站",
                        "B2K037": "深圳北汽车客运站",
                        "B1K010": "皇岗汽车客运站",
                        "B2K040": "机场汽车客运站",
                        }
        for k, v in station_dict.items():
            data = {
                "stationCode": k,
                }
            yield scrapy.FormRequest(start_url,
                                     method="POST",
                                     formdata=data,
                                     callback=self.parse_target_city,
                                     meta={"start_code": k})

    def parse_target_city(self, response):
        start_code = response.meta["start_code"]
        res = json.loads(response.body)
        if not res["success"]:
            self.logger.error("parse_target_city: Unexpected return, %s", res)
            return
        line_url = "http://www.vchepiao.cn/mb/base/bus/queryBusSKY"
        end_list = res['data']
        for end in end_list:
            today = datetime.date.today()
            for j in range(1, 7):
                sdate = str(today+datetime.timedelta(days=j))
                sdate_tra = sdate.replace('-', '')
#                 if self.has_done(start[1], end["depotName"], sdate):
#                     self.logger.info("ignore %s ==> %s %s" % (start[1], end["depotName"], sdate))
#                     continue
                data = {
                    "fromCity": "深圳",
                    "stationCode": start_code,
                    "dstNode": end['NDName'],
                    "schDate": sdate_tra
                }
                yield scrapy.FormRequest(line_url,
                                         method="POST",
                                         formdata=data,
                                         callback=self.parse_line,
                                         meta={"start_code": start_code, "end": end, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        start_code = response.meta["start_code"]
        end = response.meta["end"]
        sdate = response.meta["date"]
#         self.mark_done(start[1], end["depotName"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
#         if  res["values"]["resultList"]:
#             print res["values"]["resultList"]
#             print start["name"] ,end["depotName"]
        if not res["success"]:
            #self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["city_name"], end["city_name"], res["header"])
            return
        if res["data"]["list"]:
            print res
        for d in res["data"]["list"]:
            if d['SchStat'] == '1':
                attrs = dict(
                    s_province = u'广东',
                    s_city_name = u"深圳",
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(u"深圳"),
                    s_sta_name = d["SchWaitStName"],
                    s_sta_id = d["SchStationCode"],
                    d_city_name = d["SchDstCity"],
                    d_city_code=get_pinyin_first_litter(d["SchDstCity"]),
                    d_city_id = d['SchStationCode'],
                    d_sta_name = d["SchNodeName"],
                    d_sta_id = d["SchDstNode"],
                    drv_date = d["SchDate"],
                    drv_time = d["orderbytime"],
                    drv_datetime = dte.strptime("%s %s" % (d["SchDate"], d["orderbytime"]), "%Y-%m-%d %H:%M"),
                    distance = "0",
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = d["SchLocalCode"],
                    full_price = float(d["SchStdPrice"]),
                    half_price = float(d["SchStdPrice"])/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {"raw_info": d},
                    left_tickets = int(d["SchSeatCount"]),
                    crawl_source = "szky",
                    shift_id="",
                )
                yield LineItem(**attrs)


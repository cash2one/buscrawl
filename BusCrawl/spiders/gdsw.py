#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime
import urllib
import re
import time
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase
from BusCrawl.utils.tool import get_redis, get_pinyin_first_litter
from BusCrawl.utils.tool import md5


class GdswSpider(SpiderBase):
    name = "gdsw"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            # 'BusCrawl.middleware.CqkyHeaderMiddleware': 410,
        },
        # "DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        for c in [chr(i) for i in range(97, 123)]:
            start_url = "http://ticket.gdcd.gov.cn/BaseApp/BaseHandler.ashx?city=%s&gd=true" % c
            yield scrapy.Request(start_url, callback=self.parse_start_city)

    def parse_start_city(self, response):
        body = response.body.replace("\'", "\"")
        data = json.loads(body)
        today = dte.today()
        line_url = "http://183.6.161.195:9000/api/TicketOrder/QuerySchedule"
        for x in data:
            if not self.is_need_crawl(city=x):
                continue
            start = {"s_city_name": x, "s_city_code": get_pinyin_first_litter(x)}
            dest_list = self.get_dest_list("广东", x)
            for y in dest_list:
                end = {"d_city_name": y, "d_city_code": get_pinyin_first_litter(y)}
                self.logger.info("start %s ==> %s" % (start["s_city_name"], end["d_city_name"]))
                for i in range(self.start_day(), 8):
                    sdate = (today+datetime.timedelta(days=i)).strftime("%Y%m%d")
                    if self.has_done(start["s_city_name"], end["d_city_name"], sdate):
                        continue
                    params = {"fromcity": x,"schdate": sdate,"schtimeend":"","schtimestart":"","tocity":y}
                    yield scrapy.Request(line_url,
                                         method="POST",
                                         body=json.dumps(params),
                                         callback=self.parse_line,
                                         headers={"Content-Type": "application/json; charset=UTF-8"},
                                         meta={"start": start, "end": end, "sdate": sdate})

    def get_dest_list_from_web(self, province, city):
        if not hasattr(self, "_dest_list"):
            lst = []
            for c in [chr(i) for i in range(97, 123)]:
                url = "http://ticket.gdcd.gov.cn/BaseApp/BaseHandler.ashx?PurposeCity=%s" % c
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1"})
                body = r.content.replace("\'", "\"")
                data = json.loads(body)
                lst.extend(data)
            lst = set(lst)
            self._dest_list = lst
        return self._dest_list

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["s_city_name"], end["d_city_name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e

        for d in res["data"]:
            attrs = dict(
                s_province = "广东",
                s_city_id = start["s_city_id"],
                s_city_name = start["s_city_name"],
                s_sta_name = d["SchStationName"],
                s_city_code=start["s_city_code"],
                s_sta_id=d["SchStationCode"],
                d_city_name = end["d_city_name"],
                d_city_id= "",
                d_city_code=end["d_city_code"],
                d_sta_id="",
                d_sta_name=d["SchDstNodeName"],
                drv_date=d["SchDate"],
                drv_time=d["SchTime"],
                drv_datetime = dte.strptime("%s %s" % (d["SchDate"], d["SchTime"]), "%Y-%m-%d %H:%M"),
                distance = unicode(d["SchDist"]),
                vehicle_type = d["SchBusType"],
                seat_type = "",
                bus_num = d["SchLocalCode"],
                full_price = float(d["SchPrice"]),
                half_price = float(d["SchDiscPrice"]),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"raw_info": d},
                left_tickets = int(d["SchTicketCount"]),
                crawl_source = "cqky",
                shift_id="",
            )
            yield LineItem(**attrs)

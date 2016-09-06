#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib
import time

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase


class ZuocheSpider(SpiderBase):
    name = "zuoche"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
        },
        "DOWNLOAD_DELAY": 0.02,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }


    def start_requests(self):
        base_url = "http://xqt.zuoche.com/xqt/sc.jspx"
        today = dte.today()
        start = {"province": "广东", "city_name": "广州", "city_code": "gz", "city_id": ""}
        for d in self.get_dest_list(start["province"], start["city_name"]):
            end = d
            for i in range(self.start_day(), 8):
                sdate = (today+datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                params = {
                    "op": "search",
                    "date": sdate,
                    "ss": start["city_name"],
                    "ds": d["name"],
                    "ts": "0",
                    "ssn": "",
                    "dsn": "",
                    "ocb": 0,
                    "opo": 0,
                    "oxq": 0,
                    "sotp": 0,
                    "desc": 0,
                    "sign": int(time.time()*1000),
                }
                url = "%s?%s" % (base_url, urllib.urlencode(params))
                yield scrapy.Request(url, callback=self.parse_line, meta={"start": start, "end": end, "sdate": sdate})


    def get_dest_list(self, province, city, **kwargs):
        return [{"name": "深圳", "code": 'sz', "dest_id": ""}]

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if res.get("fail", True):
            return
        total_page, cur_page = int(res["page"]["count"]), int(res["page"]["page"])
        base_url = "http://xqt.zuoche.com/xqt/sc.jspx"
        if cur_page < total_page:
            params = {
                "op": "search",
                "date": sdate,
                "ss": start["city_name"],
                "ds": end["name"],
                "ts": "0",
                "ssn": "",
                "dsn": "",
                "ocb": 0,
                "opo": 0,
                "oxq": 0,
                "sotp": 0,
                "desc": 0,
                "sign": int(time.time()*1000),
                "page": cur_page+1,
                "count": total_page,
            }
            url = "%s?%s" % (base_url, urllib.urlencode(params))
            yield scrapy.Request(url, callback=self.parse_line, meta={"start": start, "end": end, "sdate": sdate})


        #self.mark_done(start["city_name"], end["name"], sdate)
        for d in res["list"]:
            if not d["canbuy"]:
                continue
            print d["time"], sdate
            drv_datetime = dte.strptime("%s %s" % (sdate, d["time"]), "%Y-%m-%d %H:%M")
            ctype = d["ctype"]
            clst = ctype.split(" ")
            if len(clst) == 2:
                bus_num, bus_type = clst[0], clst[1]
            else:
                bus_num, bus_type = ctype, ctype

            attrs = dict(
                s_province = start["province"],
                s_city_id = start["city_id"],
                s_city_name = start["city_name"],
                s_sta_name = d["stName"],
                s_city_code=start["city_code"],
                s_sta_id="",
                d_city_name = end["name"],
                d_city_id= end["dest_id"],
                d_city_code=end["code"],
                d_sta_id=end["dest_id"],
                d_sta_name=d["destName"],
                drv_date=drv_datetime.strftime("%Y-%m-%d"),
                drv_time=drv_datetime.strftime("%H:%M"),
                drv_datetime = drv_datetime,
                distance = "",
                vehicle_type = bus_type,
                seat_type = "",
                bus_num = bus_num,
                full_price = float(d["saleprice"]),
                half_price = float(d["saleprice"])/2,
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"id": d["id"]},
                left_tickets = 10,
                crawl_source = "zuoche",
                shift_id="",
            )
            print attrs
            yield LineItem(**attrs)

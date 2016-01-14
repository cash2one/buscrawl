#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime
import os
import time
import requests

from datetime import datetime as dte
from BusCrawl.items.ctrip import LineItem
from BusCrawl.utils.tool import md5
from scrapy.conf import settings


BASE_URL = "http://api.jskylwsp.cn"


class JskySpider(scrapy.Spider):
    name = "jsky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipelines.ctrip.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middlewares.common.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middlewares.common.ProxyMiddleware': 410,
            'BusCrawl.middlewares.common.JskyHeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    def __init__(self, target="", *args, **kwargs):
        self.target = target
        super(JskySpider, self).__init__(*args, **kwargs)

    def post_data_templ(self, service_name, body):
        stime = str(int(time.time()*1000))
        tmpl = {
            "body": body,
            "clientInfo": {
                "clientIp": "",
                "deviceId": "898fd52b362f6a9c",
                "extend": "4^4.4.4,5^MI 4W,6^-1",
                "macAddress": "14:f6:5a:b9:d1:4a",
                "networkType": "wifi",
                "platId": "20",
                "pushInfo": "",
                "refId": "82037323",
                "versionNumber": "1.0.0",
                "versionType": "1"
            },
            "header": {
                "accountID": "d4a45219-f2f2-4a2a-ab7b-007ee848629d",
                "digitalSign": md5(stime),
                "reqTime": stime,
                "serviceName": service_name,
                "version": "20150526020002"
            }
        }
        return tmpl

    def start_requests(self):
        dest_url = "http://api.jskylwsp.cn/ticket-interface/rest/query/getbusdestinations"
        start_list = map(lambda s: s.strip(), self.target.split(","))
        for name in start_list:
            self.logger.info("start crawl city %s", name)
            body={"departure": name}
            fd = self.post_data_templ("getbusdestinations", body)
            yield scrapy.Request(dest_url,
                                     method="POST",
                                     body=json.dumps(fd),
                                     callback=self.parse_target_city,
                                     meta={"start":{"name": name, "province": "江苏"}})

    def parse_target_city(self, response):
        res = json.loads(response.body)
        start = response.meta["start"]
        if res["header"]["rspCode"] != "0000":
            self.logger.error("parse_target_city: Unexpected return, %s %s", start["name"], res)
            return

        line_url = "http://api.jskylwsp.cn/ticket-interface/rest/query/getbusschedule"

        days_url = "http://api.jskylwsp.cn/ticket-interface/rest/query/getbussaleday"
        body={"departure": start["name"]}
        data = self.post_data_templ("getbussaleday", body)
        headers = {
            "User-Agent": "Dalvik/1.6.0 (Linux; U; Android 4.4.4; MI 4W MIUI/V7.1.3.0.KXDCNCK)",
            "Content-Type": "application/json; charset=UTF-8",
        }
        r = requests.post(days_url, data=json.dumps(data), headers=headers)
        sale_day_info = r.json()
        days = int(sale_day_info["body"]["saleDays"])

        for info in res["body"]["destinationList"]:
            for city in info["cities"]:
                end = {
                    "name": city["name"],
                    "pinyin": city["enName"],
                    "short_pinyin": city["shortEnName"],
                }
                self.logger.info("start %s ==> %s" % (start["name"], city["name"]))

                # 预售期10天
                today = datetime.date.today()
                for i in range(0, days+1):
                    sdate = str(today+datetime.timedelta(days=i))
                    body = {
                        "departure": start["name"],
                        "destination": end["name"],
                        "dptDate": sdate,
                        "pageIndex": 1,
                        "pageSize": 1025,
                    }
                    fd = self.post_data_templ("getbusschedule", body)
                    yield scrapy.Request(line_url, method="POST", body=json.dumps(fd), callback=self.parse_line, meta={"start": start, "end": end, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate =  response.meta["date"]
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if int(res["header"]["rspCode"]) != 0:
            self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["name"], end["name"], res["header"])
            return
        for d in res["body"]["scheduleList"]:
            if int(d["canBooking"]) != 1:
                continue
            left_tickets = int(d["ticketLeft"])
            from_city = unicode(d["departure"])
            to_city = unicode(d["destination"])
            from_station = unicode(d["dptStation"])
            to_station = unicode(d["arrStation"])

            attrs = dict(
                s_province = start["province"],
                s_city_name = from_city,
                s_sta_name = from_station,
                d_city_name = to_city,
                d_sta_name = to_station,
                line_id = md5("%s-%s-%s-%s-%s-jsky" % (from_city, to_city, from_station, to_station, d["dptDateTime"])),
                drv_date = d["dptDate"],
                drv_time = d["dptTime"],
                drv_datetime = dte.strptime("%s %s" % (d["dptDate"], d["dptTime"]), "%Y-%m-%d %H:%M"),
                distance = unicode(d["distance"]),
                vehicle_type = d["coachType"],
                seat_type = "",
                bus_num = d["coachNo"],
                full_price = float(d["ticketPrice"]),
                half_price = float(d["childPrice"]),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"raw_info": d},
                left_tickets = left_tickets,
                crawl_source = "jsky",
            )
            yield LineItem(**attrs)

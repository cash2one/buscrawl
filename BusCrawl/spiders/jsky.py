#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime
import time
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import md5, get_pinyin_first_litter
from base import SpiderBase


BASE_URL = "http://api.jskylwsp.cn"


class JskySpider(SpiderBase):
    name = "jsky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.JskyHeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

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
        line_url = "http://api.jskylwsp.cn/ticket-interface/rest/query/getbusschedule"
        for name in ["苏州", "南京", "无锡", "常州", "南通", "张家港", "昆山", "吴江", "常熟", "太仓", "镇江", "宜兴", "江阴", "兴化", "盐城", "扬州", "连云港", "徐州", "宿迁", "泰州"]:
            if not self.is_need_crawl(city=name):
                continue
            self.logger.info("start crawl city %s", name)
            start = {"name": name, "province": "江苏"}
            for s in self.get_dest_list(start["province"], start["name"]):
                name, code = s.split("|")
                end = {"name": name, "short_pinyin": code}
                self.logger.info("start %s ==> %s" % (start["name"], end["name"]))

                today = datetime.date.today()
                for i in range(self.start_day(), 7):
                    sdate = str(today+datetime.timedelta(days=i))
                    if self.has_done(start["name"], end["name"], sdate):
                        self.logger.info("ignore %s ==> %s %s" % (start["name"], end["name"], sdate))
                        continue
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
        sdate = response.meta["date"]
        self.mark_done(start["name"], end["name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if int(res["header"]["rspCode"]) != 0:
            #self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["name"], end["name"], res["header"])
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
                s_city_id = "",
                s_city_name = from_city,
                s_city_code=get_pinyin_first_litter(from_city),
                s_sta_name = from_station,
                s_sta_id="",
                d_city_name = to_city,
                d_city_id="",
                d_city_code=end["short_pinyin"],
                d_sta_name = to_station,
                d_sta_id="",
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
                shift_id="",
            )
            yield LineItem(**attrs)

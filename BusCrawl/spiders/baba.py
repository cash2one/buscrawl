#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import time

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_redis


class BabaSpider(scrapy.Spider):
    name = "baba"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.BabaHeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        #"RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def __init__(self, target="", *args, **kwargs):
        self.target = target
        super(BabaSpider, self).__init__(*args, **kwargs)

    def post_data_templ(self, content):
        tmpl = {
            "content": content,
            "common": {
                "pushToken": "864895020513527",
                "channelVer": "BabaBus",
                "usId": "",
                "appId": "com.hundsun.InternetSaleTicket",
                "appVer": "1.0.0",
                "loginStatus": "0",
                "imei": "864895020513527",
                "mobileVer": "4.4.4",
                "terminalType": "1"
            },
            "key": ""
        }
        return tmpl

    def start_requests(self):
        start_url = "http://s4mdata.bababus.com:80/app/v3/ticket/cityAllListFrom.htm"
        content = {"dataVersion": ""}
        fd = self.post_data_templ(content)
        yield scrapy.Request(start_url,
                             method="POST",
                             body=json.dumps(fd),
                             callback=self.parse_start_city)

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["returnNo"] != "0000":
            self.logger.error("parse_start_city: Unexpected return, %s", res)
            return
        dest_url = "http://s4mdata.bababus.com:80/app/v3/ticket/getStationList.htm"
        letters = [chr(i) for i in range(97,123)]
        start_list = map(lambda s: s.strip(), self.target.split(","))
        for info in res["content"]["cityList"]:
            if start_list and info["cityName"] not in start_list:
                continue
            start = {
                "province": "浙江",
                "city_name": info["cityName"],
                "city_code": info["allSpell"],
                "city_id": info["cityId"],
            }
            for c in letters:
                content = {"searchType": "1", "dataName": c}
                fd = self.post_data_templ(content)
                yield scrapy.Request(dest_url,
                                    method="POST",
                                    body=json.dumps(fd),
                                    callback=self.parse_target_city,
                                    meta={"start": start})

    def mark_done(self, s_name, d_name, sdate):
        r = get_redis()
        t = time.time()
        k = "%s_%s_%s" % (s_name, d_name, sdate)
        r.hset("line:done:baba", k, t)

    def has_done(self, s_name, d_name, sdate):
        r = get_redis()
        k = "%s_%s_%s" % (s_name, d_name, sdate)
        now = time.time()
        t = r.hget("line:done:baba", k)
        t = float(t or 0)
        if now - t>12 * 60 * 60:
            return False
        return True

    def parse_target_city(self, response):
        res = json.loads(response.body)
        start = response.meta["start"]
        if res["returnNo"] != "0000":
            self.logger.error("parse_target_city: Unexpected return, %s %s", start["name"], res)
            return

        line_url = "http://s4mdata.bababus.com:80/app/v3/ticket/busList.htm"
        days = 10
        city_list = res["content"]["toStationList"]
        if start["city_name"] == "杭州":
            days = 20
        for info in city_list:
            end = {
                "city_name": info["stationName"],
                "city_code": info["firstSpell"].lower(),
                "city_id": info["stationId"],
            }
            self.logger.info("start %s ==> %s" % (start["city_name"], end["city_name"]))

            today = datetime.date.today()
            for i in range(0, days):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start["city_name"], end["city_name"], sdate):
                    self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                    continue
                content = {
                    "pageSize": 1025,
                    "beginCityName": start["city_name"],
                    "currentPage": 1,
                    "endCityName": end["city_name"],
                    "leaveDate": sdate,
                }
                fd = self.post_data_templ(content)
                yield scrapy.Request(line_url,
                                     method="POST",
                                     body=json.dumps(fd),
                                     callback=self.parse_line,
                                     meta={"start": start, "end": end, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if res["returnNo"] != "0000":
            self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["city_name"], end["city_name"], res["header"])
            return
        self.mark_done(start["city_name"], end["city_name"], sdate)
        for d in res["content"]["busList"]:
            attrs = dict(
                s_province = start["province"],
                s_city_name = start["city_name"],
                s_city_id = start["city_id"],
                s_city_code=start["city_code"],
                s_sta_name = d["beginStation"],
                s_sta_id = d["beginStationId"],
                d_city_name = end["city_name"],
                d_city_code=end["city_code"],
                d_city_id = end["city_id"],
                d_sta_name = d["endStation"],
                d_sta_id = d["endStationId"],
                drv_date = d["leaveDate"],
                drv_time = d["leaveTime"],
                drv_datetime = dte.strptime("%s %s" % (d["leaveDate"], d["leaveTime"]), "%Y-%m-%d %H:%M"),
                distance = "0",
                vehicle_type = "",
                seat_type = "",
                bus_num = d["busId"],
                full_price = float(d["fullPrice"]),
                half_price = float(d["fullPrice"])/2,
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"depotName": d["depotName"], "sbId": d["sbId"], "stId": d["stId"], "depotId": d["depotId"]},
                left_tickets = int(d["remainCount"]),
                crawl_source = "baba",
                shift_id="",
            )
            yield LineItem(**attrs)

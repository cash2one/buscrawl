#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import time
import urllib

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase
from BusCrawl.utils.tool import md5

#API_BASE_URL = "http://testapi.fangbian.com:6801/fbapi.asmx"
API_BASE_URL = "http://qcapi.fangbian.com/fbapi.asmx"


class FangBianSpider(SpiderBase):
    name = "fangbian"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.FangBianHeaderMiddleware': 410,
        },
    }

    def post_data_templ(self, service_id, sdata):
        ts = int(time.time())
        code = "car12308com"
        key = "car12308com201510"
        tmpl = {
            "merchantCode": code,
            "version": "1.4.0",
            "timestamp": ts,
            "serviceID": service_id,
            "data": sdata,
            "sign": md5("%s%s%s%s%s" % (code, service_id, ts, sdata, md5(key))),
        }
        return tmpl

    def start_requests(self):
        start_url = API_BASE_URL + "/Query"
        fd = self.post_data_templ("U0101", "")
        yield scrapy.Request(start_url,
                             method="POST",
                             body=urllib.urlencode(fd),
                             callback=self.parse_start_city)

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["code"] != 1101:
            self.logger.error("parse_start_city: Unexpected return, %s", res["message"])
            return
        dest_url = API_BASE_URL + "/Query"
        for info in res["data"]:
            province = info["province"]
            for d in info["cityList"]:
                city_info = d["city"]
                if not int(city_info["IsCanOrder"]):
                    continue
                start = {
                    "province": province,
                    "city_name": city_info["Region"],
                    "city_code": city_info["Region_Code"],
                    "city_id": "",
                    "presell_day": int(city_info["presellDay"]),
                }
                fd = self.post_data_templ("U0102", start["city_name"])
                yield scrapy.Request(dest_url,
                                     method="POST",
                                     body=urllib.urlencode(fd),
                                     callback=self.parse_target_city,
                                     meta={"start": start})

    def parse_target_city(self, response):
        res = json.loads(response.body)
        if res["code"] != 1102:
            self.logger.error("parse_target_city: Unexpected return, %s", res["message"])
            return
        start = response.meta["start"]
        line_url = API_BASE_URL + "/Query"
        for d in res["data"]:
            name, code = d.split("|")
            end = {
                "city_name": name,
                "city_code": code,
                "city_id": "",
            }
            self.logger.info("start %s ==> %s" % (start["city_name"], end["city_name"]))
            today = datetime.date.today()
            for i in range(1, start["presell_day"]):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start["city_name"], end["city_name"], sdate):
                    #self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                    continue
                data = {
                    "departure": start["city_name"],
                    "dptCode": start["city_code"],
                    "destination": end["city_name"],
                    "desCode": end["city_code"],
                    "dptTime": sdate,
                    "stationCode": "",
                    "queryType": "1",
                    "exParms": ""
                }
                fd = self.post_data_templ("U0103", json.dumps(data))
                yield scrapy.Request(line_url,
                                     method="POST",
                                     body=urllib.urlencode(fd),
                                     callback=self.parse_line,
                                     meta={"start": start, "end": end, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        res = json.loads(response.body)
        if res["code"] != 1100:
            # self.logger.error("parse_line: Unexpected return, %s", res["message"])
            return
        self.mark_done(start["city_name"], end["city_name"], sdate)
        for d in res["data"]:
            drv_datetime = dte.strptime("%s %s" % (d["dptDate"], d["dptTime"]), "%Y-%m-%d %H:%M:%S")
            attrs = dict(
                s_province = start["province"],
                s_city_name = start["city_name"],
                s_city_id = start["city_id"],
                s_city_code=start["city_code"],
                s_sta_name = d["dptStation"],
                s_sta_id = d["stationCode"],
                d_city_name = end["city_name"],
                d_city_code=end["city_code"],
                d_city_id = end["city_id"],
                d_sta_name = d["arrStation"],
                d_sta_id = "",
                drv_date = drv_datetime.strftime("%Y-%m-%d"),
                drv_time = drv_datetime.strftime("%H:%M"),
                drv_datetime = drv_datetime,
                distance = "0",
                vehicle_type = d["coachType"],
                seat_type = "",
                bus_num = d["coachNo"],
                full_price = float(d["ticketPrice"]),
                half_price = float(d["ticketPrice"])/2,
                fee = float(d["fee"]),
                crawl_datetime = dte.now(),
                extra_info = {"exData1": d["exData1"], "exData2": d["exData2"]},
                left_tickets = int(d["ticketLeft"] or 0),
                crawl_source = "fangbian",
                shift_id="",
            )
            yield LineItem(**attrs)

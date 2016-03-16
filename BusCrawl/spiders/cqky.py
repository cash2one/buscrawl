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


class CqkySpider(SpiderBase):
    name = "cqky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.CqkyProxyMiddleware': 410,
            'BusCrawl.middleware.CqkyHeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        start_url = "http://www.96096kp.com/StationSelect3.aspx"
        yield scrapy.Request(start_url,
                             callback=self.parse_start_city,)

    def get_dest_list(self, start_info):
        rds = get_redis()
        rds_key = "crawl:dest:cqky:%s" % start_info["s_city_name"]
        dest_str = rds.get(rds_key)
        if not dest_str:
            ts = int(time.time())
            code = "car12308com"
            key = "car12308com201510"
            service_id = "U0102"
            sdata = start_info["s_city_name"]
            if sdata == "重庆主城":
                sdata="重庆"
            tmpl = {
                "merchantCode": code,
                "version": "1.4.0",
                "timestamp": ts,
                "serviceID": service_id,
                "data": sdata,
                "sign": md5("%s%s%s%s%s" % (code, service_id, ts, sdata, md5(key))),
            }
            base_url = "http://qcapi.fangbian.com/fbapi.asmx/Query"
            r = requests.post(base_url,
                              data=urllib.urlencode(tmpl),
                              headers={"User-Agent": "Chrome", "Content-Type": "application/x-www-form-urlencoded"})
            lst = r.json()["data"]
            dest_str = json.dumps(lst)
            rds.set(rds_key, dest_str)
        lst = json.loads(dest_str)
        return lst

    def parse_start_city(self, response):
        res = json.loads(re.findall(r"var _stationList=(\S+)</script>", response.body)[0].replace("Pros", '"Pros"').replace("Areas", '"Areas"').replace("Stations", '"Stations"'))
        line_url = "http://www.96096kp.com/UserData/MQCenterSale.aspx"
        for d in res["Areas"][0]["AreaData"]:
            start = {
                "province": "重庆",
                "s_city_id": d["ID"],
                "s_city_name": d["CityDist"],
                "s_city_code": get_pinyin_first_litter(d["CityDist"]),
            }
            if not self.is_need_crawl(city=start["s_city_name"]):
                continue
            for s in self.get_dest_list(start):
                name, code = s.split("|")
                end = {"d_city_name": name, "d_city_code": code}
                today = datetime.date.today()
                self.logger.info("start %s ==> %s" % (start["s_city_name"], end["d_city_name"]))
                for i in range(1, 6):
                    sdate = str(today + datetime.timedelta(days=i))
                    if self.has_done(start["s_city_name"], end["d_city_name"], sdate):
                        # self.logger.info("ignore %s ==> %s %s" % (start["s_city_name"], end["d_city_name"], sdate))
                        continue
                    params = {
                        "StartStation": start["s_city_name"],
                        "WaitStationCode": "",
                        "OpStation": -1,
                        "OpAddress": -1,
                        "SchDate": sdate,
                        "DstNode": name,
                        "SeatType": "",
                        "SchTime": "",
                        "OperMode": "",
                        "SchCode": "",
                        "txtImgCode": "",
                        "cmd": "MQCenterGetClass",
                        "isCheck": "false",
                    }
                    yield scrapy.Request(line_url,
                                         method="POST",
                                         body=urllib.urlencode(params),
                                         callback=self.parse_line,
                                         meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["s_city_name"], end["d_city_name"], sdate)
        content = response.body
        for k in set(re.findall("([A-Za-z]+):", content)):
            content = re.sub(r"\b%s\b" % k, '"%s"' % k, content)

        try:
            res = json.loads(content)
        except Exception, e:
            self.logger.error("parse_line: %s" % content)
            raise e
        if res["success"] != "true":
            self.logger.error("parse_line: Unexpected return, %s" % res)
            return

        for d in res["data"]:
            attrs = dict(
                s_province = start["province"],
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

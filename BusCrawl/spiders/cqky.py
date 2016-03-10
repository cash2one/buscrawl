#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime
import urllib
import re
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase
from BusCrawl.utils.tool import get_redis, get_pinyin_first_litter


class CqkySpider(SpiderBase):
    name = "cqky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.CqkyHeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        start_url = "http://www.96096kp.com/StationSelect3.aspx"
        yield scrapy.Request(start_url,
                             callback=self.parse_start_city,)

    # def get_dest_list(self, start_info):
    #     rds = get_redis()
    #     rds_key = "crawl:dest:cqky:%s" % start_info["s_city_id"]
    #     dest_str = rds.get(rds_key)
    #     if not dest_str:
    #         dest_url = "http://www.96096kp.com/UserData/MQCenterSale.aspx"
    #         dest_list = set([])
    #         headers = {
    #             "Content-Type": "application/x-www-form-urlencoded",
    #             "Origin": "http://www.96096kp.com/Default.aspx",
    #             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36",
    #             "Referer": "http://www.96096kp.com/Default.aspx"
    #         }
    #         for c in [chr(i) for i in range(97, 123)]:
    #             params= {
    #                 "cmd": "QueryNode",
    #                 "StartStation": start_info["s_city_name"],
    #                 "q": c,
    #             }
    #             r = requests.post(dest_url,
    #                               data=urllib.urlencode(params),
    #                               headers=headers,)
    #             res = r.json()
    #             for d in res:
    #                 dest_list.add((d["NDCode"], d["NDName"]))
    #         dest_str = json.dumps(list(dest_list))
    #         rds.set(rds_key, dest_str)
    #         rds.expire(rds_key, 5*24*60*60)
    #     lst = json.loads(dest_str)
    #     return lst

    def get_dest_list(self, start):
        rds = get_redis()
        return list(rds.smembers("cqky_all_dest"))

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
            for name in self.get_dest_list(start):
                end = {"d_city_name": name, "d_city_code": get_pinyin_first_litter(unicode(name))}
                today = datetime.date.today()
                self.logger.info("start %s ==> %s" % (start["s_city_name"], end["d_city_name"]))
                for i in range(1, 5):
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
            raise e
        if res["success"] != "true":
            self.logger.error("parse_target_city: Unexpected return, %s" % res)
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

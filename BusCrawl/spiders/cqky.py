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
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        start_url = "http://www.96096kp.com/StationSelect3.aspx"
        yield scrapy.Request(start_url,
                             callback=self.parse_start_city,)

    def get_dest_list(self, start_info):
        dest_url = "http://www.96096kp.com/UserData/MQCenterSale.aspx"
        dest_list = set([])
        ua = "Mozilla/5.0 (Linux; U; Android 2.2; fr-lu; HTC Legend Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko)  Version/4.0 Mobile Safari/533.1"
        headers = {
            "User-Agent": ua,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.get("http://www.96096kp.com/", headers={"User-Agent": headers["User-Agent"]})
        print 111111, r.cookies
        for c in [chr(i) for i in range(97, 123)]:
            params= {
                "cmd": "QueryNode",
                "StartStation": start_info["s_city_name"],
                "q": c,
            }
            r = requests.post(dest_url,
                              data=urllib.urlencode(params),
                              headers=headers,
                              cookies=r.cookies)
            print r.content
            res = r.json()
            for d in res:
                dest_list.add((d["NDCode"], d["NDName"]))
        return dest_list

    def parse_start_city(self, response):
        res = json.loads(re.findall(r"var _stationList=(\S+)</script>", response.body)[0].replace("Pros", '"Pros"').replace("Areas", '"Areas"').replace("Stations", '"Stations"'))
        for d in res["Areas"][0]["AreaData"]:
            start = {
                "province": "重庆",
                "s_city_id": d["ID"],
                "s_city_name": d["CityDist"],
            }
            print self.get_dest_list(start)
            break

    def parse_target_city(self, response):
        c = response.body
        c = c[c.index("["): c.rindex("]") + 1]
        for s in ["endId", "endName", "endPinyin", "endPinyinUrl", "stationMapIds", "endFirstLetterAll", "endCityNameDesc", "repeatFlag", "upEndName", "showName", "endTypeId", "provinceId", "provinceName"]:
            c=c.replace("%s:" % s, "\"%s\":" % s)
        c = c.replace("'", "\"")
        res = json.loads(c)

        line_url = "http://www.changtu.com/chepiao/querySchList.htm"
        start = response.meta["start"]
        for city in res:
            end = {
                "id": city["endId"],
                "name": city["showName"],
                "pinyin": city["endPinyinUrl"],
                "short_pinyin": city["endFirstLetterAll"],
                "end_type": city["endTypeId"],
            }
            self.logger.info("start %s ==> %s" % (start["name"], end["name"]))

            today = datetime.date.today()
            for i in range(1, 10):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start["name"], end["name"], sdate):
                    #self.logger.info("ignore %s ==> %s %s" % (start["name"], d["name"], sdate))
                    continue
                params = dict(
                    endTypeId=end["end_type"],
                    endId=end["id"],
                    planDate=sdate,
                    startCityUrl=start["pinyin"],
                    endCityUrl=end["pinyin"],
                    querySch=0,
                    startCityId=start["id"],
                    endCityId=end["id"],
                )
                yield scrapy.Request("%s?%s" % (line_url, urllib.urlencode(params)),
                                     callback=self.parse_line,
                                     meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["name"], end["name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            print response.body
            raise e
        if res["bookFlag"] != "Y":
            self.logger.error("parse_target_city: Unexpected return, %s" % res)
            return

        for d in res["schList"]:
            if int(d["bookFlag"]) != 2:
                continue

            attrs = dict(
                s_province = start["province"],
                s_city_id = "%s|%s" % (start["id"], start["pinyin"]),
                s_city_name = start["name"],
                s_sta_name = d["localCarrayStaName"],
                s_city_code=start["short_pinyin"],
                s_sta_id=d["localCarrayStaId"],
                d_city_name = end["name"],
                d_city_id="%s|%s|%s" % (end["end_type"], end["pinyin"], end["id"]),
                d_city_code=end["short_pinyin"],
                d_sta_id=d["stopId"],
                d_sta_name=d["stopName"],
                drv_date=d["drvDate"],
                drv_time=d["drvTime"],
                drv_datetime = dte.strptime("%s %s" % (d["drvDate"], d["drvTime"]), "%Y-%m-%d %H:%M"),
                distance = unicode(d["mile"]),
                vehicle_type = d["busTypeName"],
                seat_type = "",
                bus_num = d["scheduleId"],
                full_price = float(d["fullPrice"]),
                half_price = float(d["halfPrice"]),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"id": d["id"], "getModel": d["getModel"], "ticketTypeStr": d["ticketTypeStr"], "stationMapId": d["stationMapId"]},
                left_tickets = int(d["seatAmount"]),
                crawl_source = "changtu",
                shift_id="",
            )
            yield LineItem(**attrs)

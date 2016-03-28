#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import urllib
import datetime
import time
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_redis, get_pinyin_first_litter, md5
from base import SpiderBase


class ZjgsmSpider(SpiderBase):
    name = "zjgsm"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ZjgsmHeaderMiddleware': 410,
            'BusCrawl.middleware.ProxyMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    base_url = "http://www.zjgsmwy.com"

    def get_dest_list(self, start_city):
        rds = get_redis()
        rds_key = "crawl:dest:zjgsm:%s" % start_city
        dest_str = rds.get(rds_key)
        if not dest_str:
            ts = int(time.time())
            code = "car12308com"
            key = "car12308com201510"
            service_id = "U0102"
            sdata = start_city
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

    def start_requests(self):
        # 这是个pc网页页面
        start_url = self.base_url+"/busticket/busticket/service/Busticket.getAreaList.json"
        yield scrapy.FormRequest(start_url,
                                callback=self.parse_start_city)

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["rtnCode"] != "000000":
            self.logger.error("parse_start_city: Unexpected return, %s" % res["rtnMsg"])
            return
        name_trans = {
            u"张家港地区": "张家港",
            u"苏州市区": "苏州",
            u"常熟地区": "常熟",
            u"昆山地区": "昆山",
            u"太仓地区": "太仓",
            u"吴江地区": "吴江",
        }
        station_url =self.base_url+"/busticket/busticket/service/Busticket.getStationList.json"
        for d in res["responseData"]:
            city = {
                "city_id": d["areacode"],
                "city_name": name_trans[d["areaname"]],
            }
            if not self.is_need_crawl(city=city["city_name"]):
                continue
            yield scrapy.FormRequest(station_url,
                                     formdata={"AREACODE": city["city_id"]},
                                     callback=self.parse_start_station,
                                     meta={"start": city})

    def parse_start_station(self, response):
        res = json.loads(response.body)
        start = response.meta["start"]
        if res["rtnCode"] != "000000":
            self.logger.error("parse_start_station: Unexpected return, %s" % res["rtnMsg"])
            return
        line_url = self.base_url + "/busticket/busticket/service/Busticket.getBusTicketList.json"
        for d in res["responseData"]:
            start["sta_name"] = d["stationname"]
            for s in self.get_dest_list(start["city_name"]):
                name, code = s.split("|")
                end = {"city_name": name, "city_code": code}
                self.logger.info("start %s ==> %s" % (start["sta_name"], end["city_name"]))
                today = datetime.date.today()
                for i in range(self.start_day(), 6):
                    sdate = str(today + datetime.timedelta(days=i))
                    if self.has_done(start["sta_name"], end["city_name"], sdate):
                        continue
                    params = {
                        "AREACODE": start["city_id"],
                        "ONSTAION": start["sta_name"],
                        "OFFSTATION": end["city_name"],
                        "STARTDATE": sdate,
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
        self.mark_done(start["sta_name"], end["city_name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            self.logger.error(response.body)
            raise e
        if res["rtnCode"] != "000000":
            self.logger.error("parse_line: Unexpected return, %s" % res["rtnMsg"])
            return
        shift_list = res["responseData"]["shiftList"] or []

        for d in shift_list:
            drv_datetime = dte.strptime("%s %s" % (d["startdate"], d["starttime"]), "%Y%m%d %H%M")
            attrs = dict(
                s_province = "江苏",
                s_city_id = start["city_id"],
                s_city_name = start["city_name"],
                s_sta_name = d["onstation"],
                s_city_code=get_pinyin_first_litter(unicode(start["city_name"])),
                s_sta_id="",
                d_city_name = end["city_name"],
                d_city_id="",
                d_city_code=end["city_code"],
                d_sta_id=d["offstationcode"],
                d_sta_name = d["offstation"],
                drv_date = drv_datetime.strftime("%Y-%m-%d"),
                drv_time = drv_datetime.strftime("%H:%M"),
                drv_datetime = drv_datetime,
                distance = unicode(d["distance"]),
                vehicle_type = d["bustype"],
                seat_type = "",
                bus_num = d["shift"],
                full_price = float(d["price"]),
                half_price = float(d["halfprice"]),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"startstation": d["startstation"], "terminalstation": d["terminalstation"]},
                left_tickets = d["availablenum"],
                crawl_source = "zjgsm",
                shift_id="",
            )
            yield LineItem(**attrs)

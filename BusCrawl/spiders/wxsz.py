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


class WxszSpider(SpiderBase):
    name = "wxsz"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            # 'BusCrawl.middleware.ZjgsmHeaderMiddleware': 410,
            'BusCrawl.middleware.ProxyMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.5,
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
        start_url = "http://coach.wisesz.mobi/coach_v38/main/getstations"
        yield scrapy.FormRequest(start_url,
                                 callback=self.parse_start_city)

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["errorCode"] != 0:
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
        line_url = "http://coach.wisesz.mobi/coach_v38/main/get_tickets"
        for d in res["data"]["dataList"]:
            start = {
                "city_id": d["FIELDS1"],
                "city_name": name_trans[d["FIELDS2"]],
            }
            if not self.is_need_crawl(city=start["city_name"]):
                continue
            for sta in d["stations"]:
                start.update({
                    "sta_name": sta["FIELDS3"],
                    "sta_id": sta["FIELDS2"],
                })
                for s in self.get_dest_list(start["city_name"]):
                    name, code = s.split("|")
                    end = {"city_name": name, "city_code": code}
                    self.logger.info("start %s ==> %s" % (start["sta_name"], end["city_name"]))
                    today = datetime.date.today()
                    for i in range(self.start_day(), 6):
                        sdate = (today + datetime.timedelta(days=i)).strftime("%Y%m%d")
                        if self.has_done(start["sta_name"], end["city_name"], sdate):
                            continue
                        params = {
                            "departdate": sdate,
                            "destination": end["city_name"],
                            "fromcode": start["sta_id"],
                            "from": start["sta_name"],
                        }
                        yield scrapy.Request("%s?%s" % (line_url, urllib.urlencode(params)),
                                             method="POST",
                                             callback=self.parse_line,
                                             headers={"Content-Type": "application/json;charset=UTF-8"},
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
        if res["errorCode"] != 0:
            self.logger.error("parse_line: Unexpected return, %s", res)
            return
        shift_list = res["data"]["dataList"] or []

        for d in shift_list:
            drv_datetime = dte.strptime("%s %s" % (d["FIELDS1"], d["FIELDS3"]), "%Y%m%d %H%M")
            attrs = dict(
                s_province = "江苏",
                s_city_id = start["city_id"],
                s_city_name = start["city_name"],
                s_sta_name = d["FIELDS4"],
                s_city_code=get_pinyin_first_litter(unicode(start["city_name"])),
                s_sta_id= d["fromcode"],
                d_city_name = end["city_name"],
                d_city_id="",
                d_city_code=end["city_code"],
                d_sta_id=d["FIELDS11"],
                d_sta_name = d["FIELDS5"],
                drv_date = drv_datetime.strftime("%Y-%m-%d"),
                drv_time = drv_datetime.strftime("%H:%M"),
                drv_datetime = drv_datetime,
                distance = unicode(d["FIELDS16"]),
                vehicle_type = d["FIELDS9"],
                seat_type = "",
                bus_num = d["FIELDS2"],
                full_price = float(d["FIELDS14"]),
                half_price = float(d["FIELDS15"]),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"startstation": d["FIELDS17"], "terminalstation": d["FIELDS6"]},
                left_tickets = int(d["FIELDS10"]),
                crawl_source = "wxsz",
                shift_id="",
            )
            yield LineItem(**attrs)

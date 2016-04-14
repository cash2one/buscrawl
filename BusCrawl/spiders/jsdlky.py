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
from BusCrawl.utils.tool import get_redis, md5
from base import SpiderBase

START_STA_LIST = [
    {"query_code": "njkynz","stname":'南京客运南站'},
    {"query_code": 'njdz',"stname":'南京东站'},
    {"query_code": 'njbz',"stname":'南京北站'},
    {"query_code": 'jnkyz',"stname":'江宁客运站'},
    {"query_code": 'gcz',"stname":'高淳站'},
    {"query_code": 'lsz',"stname":'溧水站'},
    {"query_code": 'njgtz',"stname":'南京葛塘站'},
    {"query_code": 'njqckyz',"stname":'南京汽车客运站(小红山站)'}
]


class JsdlkySpider(SpiderBase):
    name = "jsdlky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            # 'BusCrawl.middleware.ZjgsmHeaderMiddleware': 410,
            'BusCrawl.middleware.ProxyMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def get_dest_list(self, start_city):
        rds = get_redis()
        rds_key = "crawl:dest:jsdlky:%s" % start_city
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
        line_url = "http://58.213.132.27:8082/nj_weixinService/2.0/queryBus"
        today = datetime.date.today()
        for sta_info in START_STA_LIST:
            start = {
                "city_name": "南京",
                "city_code": "nj",
                "sta_name": sta_info["stname"],
                "sta_code": sta_info["query_code"],
            }
            for s in self.get_dest_list(start["city_name"]):
                name, code = s.split("|")
                end = {"city_name": name, "city_code": code}
                self.logger.info("start %s ==> %s" % (start["sta_name"], end["city_name"]))
                for i in range(self.start_day(), 7):
                    sdate = (today + datetime.timedelta(days=i)).strftime("%Y%m%d")
                    if self.has_done(start["sta_name"], end["city_name"], sdate):
                        continue
                    params = {
                        "drive_date": sdate,
                        "rst_name": start["sta_name"],
                        "dst_name": end["city_name"],
                        "v_source": "a",
                        "v_version": "v2.2",
                        "v_reg_id": ""
                    }
                    req_data = {
                        "param_key": json.dumps(params),
                        "secret_key": md5("&".join(map(lambda a:"%s=%s" % (a[0], a[1]), sorted(params.items(), key=lambda i: i[0])))),
                    }
                    yield scrapy.Request("%s?%s" % (line_url, urllib.urlencode(req_data)),
                                         callback=self.parse_line,
                                         meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["sta_name"], end["city_name"], sdate)
        res = json.loads(response.body)
        if res["rtn_code"] != "00":
            self.logger.error("parse_line: Unexpected return, %s", res)
            return
        shift_list = res["data"] or []

        for d in shift_list:
            drv_datetime = dte.strptime("%s %s" % (d["drive_date"], d["plan_time"]), "%Y%m%d %H%M")
            attrs = dict(
                s_province = "江苏",
                s_city_id = "",
                s_city_name = start["city_name"],
                s_sta_name = d["rst_name"],
                s_city_code= start["city_code"],
                s_sta_id= d["rstcode"],
                d_city_name = end["city_name"],
                d_city_id="",
                d_city_code=end["city_code"],
                d_sta_id=d["dstcode"],
                d_sta_name = d["dst_name"],
                drv_date = drv_datetime.strftime("%Y-%m-%d"),
                drv_time = drv_datetime.strftime("%H:%M"),
                drv_datetime = drv_datetime,
                distance = unicode(d["mileage"]),
                vehicle_type = d["m_name"],
                seat_type = "",
                bus_num = d["bus_code"],
                full_price = float(d["full_price"]),
                half_price = float(d["half_price"]),
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"startstation": d["sst_name"], "terminalstation": d["tst_name"], "startstationcode": d["sstcode"]},
                left_tickets = int(d["available_tickets"]),
                crawl_source = "jsdlky",
                shift_id="",
            )
            yield LineItem(**attrs)

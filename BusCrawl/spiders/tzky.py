#!/usr/bin/env python
# encoding: utf-8

import scrapy
import datetime
import urllib
import re

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase
from bs4 import BeautifulSoup


class TzkySpider(SpiderBase):
    name = "tzky"
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
        dest_url = "http://www.tzfeilu.com:8086/script/js/dstcity.js"
        yield scrapy.Request(dest_url, callback=self.parse_target_city)

    def parse_target_city(self, response):
        station_list = ["泰州南站", "泰州京泰站", "高港北站"]
        line_url = "http://www.tzfeilu.com:8086/index.php/search/getBuslist"
        today = datetime.date.today()
        for ds in re.findall(r"\"(\S+)\"", response.body)[0].split("@"):
            if not ds:
                continue
            code, name, did = ds.split("|")
            end = {"city_code": code, "city_name": name, "city_id": did}
            for ss in station_list:
                start = {"sta_name": ss}
                self.logger.info("start %s ==> %s" % (start["sta_name"], end["city_name"]))
                for i in range(self.start_day(), 7):
                    sdate = str(today + datetime.timedelta(days=i))
                    if self.has_done(start["sta_name"], end["city_name"], sdate):
                        continue
                    params = {
                        "ispost": 1,
                        "start_city": start["sta_name"],
                        "dd_city": end["city_name"],
                        "dd_code": end["city_id"],
                        "orderdate": sdate,
                    }
                    yield scrapy.Request(line_url,
                                         method="POST",
                                         body=urllib.urlencode(params),
                                         callback=self.parse_line,
                                         headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                                         meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["sta_name"], end["city_name"], sdate)

        soup = BeautifulSoup(response.body.replace("<!--", "").replace("-->", ""), "lxml")
        for e in soup.findAll("tr"):
            lst = e.findAll("td")
            if not lst:
                continue
            # td>MK0041</td>
            # <td>泰州南站<br/>南京</td>
            # <td>2016-04-08</td>
            # <td><span class="lv_time">05:45</span></td>
            # <td>大型高一</td>
            # <td>51</td>
            # <td><span class="tk_price">56</span></td>
            # <td><span class="lv_time">17</span></td>
            # <td>途径南京东站，终点站 : 南京南站</td><td><a href="#" onclick="if(buy_confirm('MK0041')) window.location.href='/index.php/busOrder/index/czozNTg6InsiQkNIIjoiTUswMDQxIiwiU0NaTUMiOiJcdTZjZjBcdTVkZGVcdTUzNTdcdTdhZDkiLCJTRlpETSI6IjllZDIzNDU0YjNlYWVlNDQzODEyMWJlOWM2NGNiNmUyIiwiRERaTUMiOiJcdTUzNTdcdTRlYWMiLCJERFpETSI6IjBlMmYwY2U4YmQ5MDk1NThkYWViMjFjNTUyMGI3M2NhIiwiWkRaRE0iOiIwMDAwMDAwMDAiLCJTQ1pETSI6IjllZDIzNDU0YjNlYWVlNDQzODEyMWJlOWM2NGNiNmUyIiwiWkRaTUMiOiJcdTUzNTdcdTRlYWMiLCJGQ1JRIjoiMjAxNi0wNC0wOCIsIkZDU0oiOiIwNTo0NSIsIkNYIjoiXHU1OTI3XHU1NzhiXHU5YWQ4XHU0ZTAwIiwiWVBTIjoiMTciLCJIRFpXIjoiNTEiLCJRUEoiOiI1NiIsIlRQSiI6IjI4In0iOw~~';" class="buy_btn" title="购票">购票</a></td>
            bus_num = lst[0].text.strip()
            drv_date = lst[2].text.strip()
            drv_time = lst[3].text.strip()
            bus_type = lst[4].text.strip()
            price = float(lst[6].text.strip())
            left_tickets = int(lst[7].text.strip())
            attrs = dict(
                s_province = "江苏",
                s_city_id = "",
                s_city_name = "泰州",
                s_sta_name = start["sta_name"],
                s_city_code= "tz",
                s_sta_id= "",
                d_city_name = end["city_name"],
                d_city_id=end["city_id"],
                d_city_code=end["city_code"],
                d_sta_id="",
                d_sta_name=end["city_name"],
                drv_date=drv_date,
                drv_time=drv_time,
                drv_datetime = dte.strptime("%s %s" % (drv_date, drv_time), "%Y-%m-%d %H:%M"),
                distance = "0",
                vehicle_type = bus_type,
                seat_type = "",
                bus_num = bus_num,
                full_price = price,
                half_price = price/2,
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {},
                left_tickets = left_tickets,
                crawl_source = "tzky",
                shift_id="",
            )
            yield LineItem(**attrs)

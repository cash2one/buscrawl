#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase


class TongChengSpider(SpiderBase):
    name = "tongcheng"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.TongChengHeaderMiddleware': 410,
        },
        # "DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    base_url = "http://m.ctrip.com/restapi/busphp/app/index.php"

    def start_requests(self):
        # 这是个pc网页页面
        line_url = "http://m.ly.com/bus/BusJson/BusSchedule"
        for name in ["苏州", "南京", "无锡", "常州", "南通", "张家港", "昆山", "吴江", "常熟", "太仓", "镇江", "宜兴", "江阴", "兴化", "盐城", "扬州", "连云港", "徐州", "宿迁"]:
            if not self.is_need_crawl(city=name):
                continue
            self.logger.info("start crawl city %s", name)
            start = {"name": name, "province": "江苏"}
            for s in self.get_dest_list(start["province"], start["name"]):
                name, code = s.split("|")
                end = {"name": name, "short_pinyin": code}
                self.logger.info("start %s ==> %s" % (start["name"], end["name"]))

                today = datetime.date.today()
                for i in range(self.start_day(), 8):
                    sdate = str(today + datetime.timedelta(days=i))
                    if self.has_done(start["name"], end["name"], sdate):
                        self.logger.info("ignore %s ==> %s %s" % (start["name"], end["name"], sdate))
                        continue
                    params = dict(
                        Departure=start["name"],
                        Destination=end["name"],
                        DepartureDate=sdate,
                        DepartureStation="",
                        DptTimeSpan=0,
                        HasCategory="true",
                        Category="0",
                        SubCategory="",
                        ExParms="",
                        Page="1",
                        PageSize="1025",
                        BookingType="0"
                    )
                    yield scrapy.Request(line_url,
                                         method="POST",
                                         body=urllib.urlencode(params),
                                         callback=self.parse_line,
                                         meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        try:
            res = json.loads(response.body)
        except Exception, e:
            self.logger.error("%s %s", response.body, e)
            return
        res = res["response"]
        if int(res["header"]["rspCode"]) != 0:
            # self.logger.error("parse_target_city: Unexpected return, %s" % res["header"])
            return
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["name"], end["name"], sdate)

        for d in res["body"]["schedule"]:
            if not d["canBooking"]:
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
                s_sta_name = from_station,
                s_city_code=get_pinyin_first_litter(from_city),
                s_sta_id=d.get("dptStationCode",""),
                d_city_name = to_city,
                d_city_id="",
                d_city_code=end["short_pinyin"],
                d_sta_id="",
                d_sta_name = to_station,
                drv_date = d["dptDate"],
                drv_time = d["dptTime"],
                drv_datetime = dte.strptime("%s %s" % (d["dptDate"], d["dptTime"]), "%Y-%m-%d %H:%M"),
                distance = unicode(d["distance"]),
                vehicle_type = d["coachType"],
                seat_type = "",
                bus_num = d["coachNo"],
                full_price = float(d["ticketPrice"]),
                half_price = float(d["ticketPrice"])/2,
                fee = float(d["ticketFee"]),
                crawl_datetime = dte.now(),
                extra_info = {},
                left_tickets = left_tickets,
                crawl_source = "tongcheng",
                shift_id="",
            )
            yield LineItem(**attrs)

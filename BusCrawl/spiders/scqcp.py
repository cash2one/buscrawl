# -*- coding: utf-8 -*-
import scrapy
import json
import datetime

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase


class ScqcpSpider(SpiderBase):
    name = "scqcp"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.ScqcpHeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        url = "http://java.cdqcp.com/scqcp/api/v2/ticket/get_start_city"
        return [scrapy.FormRequest(url, formdata={'city_name': ''}, callback=self.parse_start_city)]

    def parse_start_city(self, response):
        "解析出发城市"
        res = json.loads(response.body)
        if int(res["status"]) != 1:
            self.logger.error("parse_start_city: Unexpected return, %s" % str(res))
            return

        url = "http://java.cdqcp.com/scqcp/api/v2/ticket/query_target_station_by_keyword"
        start_list = []
        if self.target:
            start_list = map(lambda s: s.strip(), self.target.split(","))
        for d in res["start_city"]:
            if start_list and d["city_name"] not in start_list:
                continue
            if not d["is_pre_sell"]:
                self.logger.error("%s 没开放售票", d["city_name"])
                continue
            fd = {
                "city_id": unicode(d["city_id"]),
                "city_name": unicode(d["city_name"]),
                "stop_name": "",
            }
            start = {
                "province": "四川",
                "city_id": str(d["city_id"]),
                "city_name": d["city_name"],
                "city_code": d["short_name"],
            }
            yield scrapy.FormRequest(url,
                                     formdata=fd,
                                     callback=self.parse_target_city,
                                     meta={"start": start})

    def parse_target_city(self, response):
        "解析目的地城市"
        res = json.loads(response.body)
        if int(res["status"]) != 1:
            self.logger.error("parse_target_city: Unexpected return, %s" % str(res))
            return

        url = "http://java.cdqcp.com/scqcp/api/v2/ticket/query"
        start = response.meta["start"]
        for d in res["target_city"]:
            start.update({
                "sta_id": d["carry_sta_id"],
                "sta_name": d["carry_sta_name"],
                "sta_code": d["carry_sta_id"],
            })
            end = {
                "city_name": d["stop_name"],
                "city_code": d["short_name"],
                "sta_name": d["stop_name"],
                "sta_id": "",
            }

            # 预售期5天, 节假日预售期10天
            today = datetime.date.today()
            for i in range(1, 7):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start["city_name"], end["city_name"], sdate):
                    #self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                    continue
                fd = {
                    "city_id": unicode(start["city_id"]),
                    "city_name": start["city_name"],
                    "riding_date": sdate,
                    "stop_name": d["stop_name"],
                }
                yield scrapy.FormRequest(url,
                                         formdata=fd,
                                         callback=self.parse_line,
                                         meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        res = json.loads(response.body)
        if int(res["status"]) != 1:
            #self.logger.error("parse_line: Unexpected return, %s" % str(res))
            return
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["city_name"], end["city_name"], sdate)
        for d in res["ticket_lines_query"]:
            drv_datetime = dte.strptime(d["drv_date_time"], "%Y-%m-%d %H:%M")
            drv_date, drv_time = d["drv_date_time"].split(" ")
            attrs = dict(
                s_province = start["province"],
                s_city_name = d["city"],
                s_city_id=start["city_id"],
                s_city_code=start["city_code"],
                s_sta_name = d["carry_sta_name"],
                s_sta_id=d["carry_sta_id"],
                d_city_name=d["stop_name"],
                d_city_id="",
                d_city_code=end["city_code"],
                d_sta_name =d["end_sta_name"],
                d_sta_id="",
                drv_date = drv_date,
                drv_time = drv_time,
                drv_datetime = drv_datetime,
                distance = d["mile"],
                vehicle_type = d["bus_type_name"],
                seat_type = "",
                bus_num = d["sch_id"],
                full_price = float(d["full_price"]),
                half_price = float(d["half_price"]),
                fee = float(d["service_price"]),
                crawl_datetime = dte.now(),
                extra_info = {"sign_id": d["sign_id"]},
                left_tickets = int(d["amount"]),
                crawl_source = "scqcp",
                shift_id="",
            )
            yield LineItem(**attrs)

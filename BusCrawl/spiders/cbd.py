#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime

from datetime import datetime as dte
from BusCrawl.items.ctrip import LineItem
from BusCrawl.utils.tool import md5
from scrapy.conf import settings

class CBDSpider(scrapy.Spider):
    name = "cbd"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipelines.ctrip.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middlewares.common.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middlewares.common.ProxyMiddleware': 410,
            'BusCrawl.middlewares.ctrip.HeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    base_url = "http://m.ctrip.com/restapi/busphp/app/index.php"

    def start_requests(self):
        # 这是个pc网页页面
        dest_url = "http://m.chebada.com/Home/GetBusDestinations"
        city_str = settings.get("CBD_CITYS")
        start_list = map(lambda s: s.strip(), city_str.split(","))
        for name in start_list:
            self.logger.info("start crawl city %s", name)
            fd = {
                "Departure": unicode(name),
            }
            yield scrapy.FormRequest(dest_url,
                                     formdata=fd,
                                     callback=self.parse_target_city,
                                     meta={"start":{"name": name, "province": "江苏"}})

    def parse_target_city(self, response):
        res = json.loads(response.body)
        res = res["response"]
        if int(res["header"]["rspCode"]) != 0:
            self.logger.error("parse_target_city: Unexpected return, %s" % res["header"])
            return

        line_url = "http://m.chebada.com/Schedule/GetBusSchedules"
        start = response.meta["start"]
        for info in res["body"]["destinationList"]:
            for city in info["cities"]:
                d = {
                    "name": city["name"],
                    "pinyin": city["enName"],
                    "short_pinyin": city["shortEnName"],
                }
                self.logger.info("start %s ==> %s" % (start["name"], city["name"]))

                # 预售期10天
                today = datetime.date.today()
                for i in range(0, 20):
                    sdate = str(today+datetime.timedelta(days=i))
                    params = dict(
                        departure=start["name"],
                        destination=d["name"],
                        departureDate=sdate,
                        page="1",
                        pageSize="1025",
                        hasCategory="true",
                        category="0",
                        dptTimeSpan="0",
                        bookingType="0",
                    )
                    yield scrapy.FormRequest(line_url, formdata=params, callback=self.parse_line, meta={"start": start, "end": d})

    def parse_line(self, response):
        "解析班车"
        try:
            res = json.loads(response.body)
        except Exception, e:
            print response.body
            raise e
        res = res["response"]
        if int(res["header"]["rspCode"]) != 0:
            self.logger.error("parse_target_city: Unexpected return, %s" % res["header"])
            return
        start = response.meta["start"]

        for d in res["body"]["scheduleList"]:
            if int(d["canBooking"]) != 1:
                continue
            left_tickets = int(d["ticketLeft"])
            from_city = unicode(d["departure"])
            to_city = unicode(d["destination"])
            from_station = unicode(d["dptStation"])
            to_station = unicode(d["arrStation"])

            attrs = dict(
                s_province = start["province"],
                s_city_name = from_city,
                s_sta_name = from_station,
                d_city_name = to_city,
                d_sta_name = to_station,
                line_id = md5("%s-%s-%s-%s-%s-cbd" % (from_city, to_city, from_station, to_station, d["dptDateTime"])),
                drv_date = d["dptDate"],
                drv_time = d["dptTime"],
                drv_datetime = dte.strptime("%s %s" % (d["dptDate"], d["dptTime"]), "%Y-%m-%d %H:%M"),
                distance = unicode(d["distance"]),
                vehicle_type = d["coachType"],
                seat_type = "",
                bus_num = d["coachNo"],
                full_price = float(d["ticketPrice"]),
                half_price = float(d["childPrice"]),
                fee = float(d["ticketFee"]),
                crawl_datetime = dte.now(),
                extra_info = {"raw_info": d},
                left_tickets = left_tickets,
                crawl_source = "cbd",
            )
            yield LineItem(**attrs)

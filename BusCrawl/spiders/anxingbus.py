#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime
import urllib
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase


class AnxingBusSpider(SpiderBase):
    name = "anxingbus"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.Lvtu100HeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    def start_requests(self):
        url = "http://www.anxingbus.com/sell/GetCity"
        yield scrapy.Request(url, callback=self.parse_starting)

    def get_dest_list_from_web(self, province, city, unitid=""):
        data = {"unitid": unitid, "cityName": city}
        url = "http://www.anxingbus.com/sell/GetEndStations?"+urllib.urlencode(data)
        r = requests.get(url, headers={"User-Agent": "Chrome"})
        ret = r.json()
        result = []
        for d in ret["data"][0].values():
            for city_id, city_info_str in d.items():
                lst = city_info_str.split("|")
                if city_id != lst[0]:
                    raise Exception()
                result.append({"dest_id": city_id, "name": lst[1], "code": lst[3]})
        return result

    def parse_starting(self, response):
        ret = json.loads(response.body)
        url = "http://api.lvtu100.com/products/getgoods"
        url = "http://www.anxingbus.com/sell/GetBus"

        today = datetime.date.today()
        for d in ret["data"][0].values():
            for city_id, city_info_str in d.items():
                lst = city_info_str.split("|")
                if city_id != lst[0]:
                    raise Exception()
                start = {"city_id": city_id, "city_name": unicode(lst[1]), "city_code": lst[3], "unitid": lst[9], "province": "安徽"}
                if not self.is_need_crawl(city=start["city_name"]):
                    continue
                for end in self.get_dest_list(start["province"], start["city_name"], unitid=start["unitid"]):
                    for i in range(self.start_day(), 8):
                        sdate = str(today + datetime.timedelta(days=i))
                        if self.has_done(start["city_name"], end["name"], sdate):
                            continue
                        params = {
                            "unitID": start["unitid"],
                            "busType": 0,
                            "cityID": start["city_id"],
                            "sellPlateStationID": "",
                            "sellStationID": "",
                            "endCityID": "",
                            "endStationID": end["dest_id"],
                            "busStartTime": sdate,
                            "busEndTime": "%s 23:59:59" % sdate,
                            "curPage": 1,
                            "pageSize": 1024,
                        }
                        yield scrapy.Request("%s?%s" % (url, urllib.urlencode(params)), callback=self.parse_line, meta={"start": start, "end": end, "sdate": sdate, "params": params})

    def parse_line(self, response):
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["city_name"], end["name"], sdate)
        self.logger.info("start %s ==> %s" % (start["city_name"], end["name"]))
        try:
            res = json.loads(response.body)
        except Exception, e:
            print response.body
            raise e

        print res, start["city_name"], end["name"], sdate, response.meta["params"]
        for d in res["data"]:
            drv_datetime=dte.strptime(d["BusTime"], "%Y-%m-%d %H:%M")
            attrs = dict(
                s_province=start["province"].rstrip("省"),
                s_city_id=start["city_id"],
                s_city_name=start["city_name"],
                s_sta_name=d["SellStationName"],
                s_city_code=start["city_code"],
                s_sta_id=d["SellStationID"],
                d_city_name=end["name"],
                d_city_id=end["dest_id"],
                d_city_code=end["code"],
                d_sta_id=d["StationID"],
                d_sta_name=d["StationName"],
                drv_date=drv_datetime.strftime("%Y-%m-%d"),
                drv_time=drv_datetime.strftime("%H:%M"),
                drv_datetime=drv_datetime,
                distance="",
                vehicle_type="%s(%s)" % (d["BusType"], d["Kind"]),
                seat_type="",
                bus_num=d["BusID"],
                full_price=float(d["FullPrice"]),
                half_price=float(d["HalfPrice"]) / 2,
                fee=0,
                crawl_datetime=dte.now(),
                extra_info={"UnitID": d["UnitID"], "BusGuid": d["BusGuid"], "Type": d["Type"], "IsDirect": d["IsDirect"]},
                left_tickets=int(d["SeatNum"]),
                crawl_source="anxingbus",
                shift_id="",
            )
            yield LineItem(**attrs)

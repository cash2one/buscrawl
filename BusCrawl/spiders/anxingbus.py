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

P2C = {
    "江苏": ["常州", "常熟", "滨海", "宝应", "大丰", "东海", "东台", "丹阳", "高邮", "赣榆", "灌云", "灌南", "阜宁", "海门", "洪泽", "海安", "昆山", "金坛", "句容", "江阴", "建湖", "金湖", "江都", "连云港", "溧阳", "南通", "启东", "宿迁", "苏州", "泗洪", "射阳", "泗阳", "沭阳", "如东", "如皋", "太仓", "太平", "泰州", "无锡", "吴江", "宜兴", "盐城", "扬州", "仪征", "扬中", "盱眙", "响水", "张家港", "镇江", "淮安"],
    "上海": [ "上海"],
    "安徽": [ "安庆", "巢湖", "蔡家岗", "池州", "蚌埠", "砀山", "东至", "当涂", "广德", "繁昌", "凤台", "淮北", "黄山", "含山", "宏村", "怀远", "淮南", "九华山", "马鞍山", "灵璧", "六安", "宁国", "南陵", "祁门", "庆相桥", "青阳", "泗县", "宿州", "石台", "濉溪", "铜陵", "芜湖", "湾沚", "黟县", "岩寺", "宣城", "萧县", "歙县"],
}

C2P = {}
for p, clst in P2C.items():
    for c in clst:
        C2P[unicode(c)] = unicode(p)

HEADERS = {
    "Ax-Zh": "www.anxingbus.com",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "http://www.anxingbus.com/Home/Index",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36"
}


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
        },
        # "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        url = "http://www.anxingbus.com/sell/GetCity"
        yield scrapy.Request(url, callback=self.parse_starting, headers=HEADERS)

    def get_dest_list_from_web(self, province, city, unitid=""):
    # def get_dest_list(self, province, city, unitid=""):
        data = {"unitid": unitid, "cityName": city}
        url = "http://www.anxingbus.com/sell/GetEndStations?"+urllib.urlencode(data)
        r = requests.get(url, headers=HEADERS)
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
        url = "http://www.anxingbus.com/sell/GetBus"

        today = datetime.date.today()
        for d in ret["data"][0].values():
            for city_id, city_info_str in d.items():
                lst = city_info_str.split("|")
                if city_id != lst[0]:
                    raise Exception()
                city_name = unicode(lst[1])
                if city_name not in C2P:
                    continue
                start = {"city_id": city_id, "city_name": city_name, "city_code": lst[3], "unitid": lst[9], "province": C2P[city_name]}
                if not self.is_need_crawl(city=start["city_name"], province=C2P[city_name]):
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
                            "endCityID": end["dest_id"],
                            "endStationID": "",
                            "busStartTime": sdate,
                            "busEndTime": "%s 23:59:59" % sdate,
                            "curPage": 1,
                            "pageSize": 1024,
                        }
                        yield scrapy.Request("%s?%s" % (url, urllib.urlencode(params)), callback=self.parse_line, meta={"start": start, "end": end, "sdate": sdate, "params": params}, headers=HEADERS)

    def parse_line(self, response):
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        try:
            res = json.loads(response.body)
        except Exception, e:
            print response.body
            raise e
        self.mark_done(start["city_name"], end["name"], sdate)
        self.logger.info("finish %s ==> %s %s" % (start["city_name"], end["name"], sdate))

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
                crawl_source="anxing",
                shift_id="",
            )
            yield LineItem(**attrs)

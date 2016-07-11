#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime
import time
import urllib
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import md5, get_pinyin_first_litter
from base import SpiderBase

class CBDSpider(SpiderBase):
    name = "lvtu100"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.Lvtu100HeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    base_url = "http://m.ctrip.com/restapi/busphp/app/index.php"

    def get_request_data(self, custom):
        data = {
            "appid": "lvtu100.andorid",
            "timestamp": str(int(time.time())),
            "format": "json",
            "version": "1.0",
        }
        data.update(custom)
        key_lst = filter(lambda x: data[x], data.keys())
        key_lst.sort()
        data["sign"]= md5("".join("%s%s" % (k, data[k]) for k in key_lst) + "0348ba1cbbfa0fa9ca627394e999fea5")
        return data

    def get_dest_list(self, province, city):
        """
        覆盖了父类实现
        """
        url = "http://api.lvtu100.com/products/getstopcity"
        params = self.get_request_data({"startProvince": province, "startcityname": city})
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; U; Android 2.3; en-us) AppleWebKit/999+ (KHTML, like Gecko) Safari/999.9",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = requests.post(url, data=urllib.urlencode(params), headers=headers)
        ret = r.json()
        return map(lambda d: {"city_name": d["cityname"], "province": d["province"], "city_code": d["shortspell"]}, ret["data"]["resultList"])

    def start_requests(self):
        url = "http://api.lvtu100.com/products/get_allstartcity"
        params = self.get_request_data({})
        yield scrapy.FormRequest(url, formdata=params, callback=self.parse_starting)

    def parse_starting(self, response):
        url = "http://api.lvtu100.com/products/getgoods"
        ret = json.loads(response.body)
        today = datetime.date.today()
        for city_info in ret["data"]:
            for d in city_info["lstcitys"]:
                province = d["province"]
                if not self.is_need_crawl(province=province) and not self.is_need_crawl(province=province.rstrip(u"省")):
                    continue
                start = {"city_id": d["startcityid"], "city_code": d["shortspell"], "city_name": d["cityname"], "province": d["province"]}
                if not self.is_need_crawl(city=start["city_name"]):
                    continue

                for end in self.get_dest_list(province, start["city_name"]):
                    self.logger.info("start %s ==> %s" % (start["city_name"], end["city_name"]))
                    for i in range(self.start_day(), 8):
                        sdate = str(today + datetime.timedelta(days=i))
                        if self.has_done(start["city_name"], end["city_name"], sdate):
                            continue
                        params = {
                            "startprovince": start["province"],
                            "startcity": start["city_name"],
                            "departdate": sdate,
                            "fromstation": "",
                            "pagestring": '{"page":1,"pagesize":1024}',
                            "range": "",
                            "stopprovince": end["province"],
                            "stopcity": end["city_name"],
                        }
                        yield scrapy.FormRequest(url, formdata=self.get_request_data(params), callback=self.parse_line, meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["city_name"], end["city_name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            print response.body
            raise e
        if int(res["code"]) != 0:
            self.logger.error("parse_line: Unexpected return, %s" % res)
            return

        s_sta_info = {d["productid"]: d for d in res["data"]["stations"]}
        d_sta_info = {d["productid"]: d for d in res["data"]["stopstations"]}
        for d in res["data"]["flight"]["resultList"]:
            if int(d["islocked"]) == 1:
                continue
            s_sta = s_sta_info[d["productid"]]
            d_sta = d_sta_info[d["productid"]]
            attrs = dict(
                s_province=start["province"].rstrip("省"),
                s_city_id=start["city_id"],
                s_city_name=start["city_name"],
                s_sta_name=s_sta["stationname"],
                s_city_code=start["city_code"],
                s_sta_id=s_sta["stationid"],
                d_city_name=d_sta["stopcity"],
                d_city_id="",
                d_city_code=get_pinyin_first_litter(d_sta["stopcity"]),
                d_sta_id="",
                d_sta_name=d_sta["stationname"],
                drv_date=d["departdate"],
                drv_time=d["departtime"],
                drv_datetime=dte.strptime("%s %s" % (d["departdate"], d["departtime"]), "%Y-%m-%d %H:%M"),
                distance=unicode(d["distance"] or ""),
                vehicle_type=d["bustype"] or "",
                seat_type="",
                bus_num=d["itemno"],
                full_price=float(d["price"]),
                half_price=float(d["price"]) / 2,
                fee=3,
                crawl_datetime=dte.now(),
                extra_info={"goodsid": d["goodsid"], "itemid": d["itemid"], "startProvince": start["province"], "stopprovince": end["province"], "productid": d["productid"]},
                left_tickets=10,
                crawl_source="lvtu100",
                shift_id="",
            )
            yield LineItem(**attrs)

#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urlparse
from lxml import etree
import requests
import urllib

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis
from scrapy.conf import settings
from pymongo import MongoClient


class Bus365Spider(SpiderBase):
    name = "bus365"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.Bus365HeaderMiddleware': 410,
        },
#         "DOWNLOAD_DELAY": 1,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    data = {
            "token": '{"clienttoken":"","clienttype":"android"}',
            "clienttype": "android",
            "usertoken": ''
            }

    def is_end_city(self, start, end):
        if not hasattr(self, "_sta_dest_list"):
            self._sta_dest_list = {}
        s_city_name = start['findname']

        if s_city_name not in self._sta_dest_list:
            self._sta_dest_list[s_city_name] = self.db.line.distinct('d_city_name', {'crawl_source': 'bus365', 's_city_name':s_city_name})
        result = self._sta_dest_list[s_city_name]
        if end not in result:
            return 0
        else:
            return 1

    def query_all_end_station(self, res):
        r = get_redis()
        city_id = res['id']
        netname = res['netname']
        key = "bus365_end_station:%s"%city_id
        end_station_list = r.get(key)
        if end_station_list:
            return end_station_list
        else:
            end_station_list = []
            letter = 'abcdefghijklmnopqrstuvwxyz'
            for i in letter:
                for j in letter:
                    query = i+j
                    url = 'http://%s/schedule/reachstations2/0'%netname
                    req_data = {
                        "cityid": city_id,
                        "word": query,
                        "page": "1",
                        "rowCount": "100",
                    }
                    req_data.update(self.data)
                    station_url = "%s?%s" % (url, urllib.urlencode(req_data))
                    res = requests.get(station_url)
                    res = res.json()
                    for res_list in res['data']:
                        end_station_list.append(res_list['name'])
            r.set(key, json.dumps(list(set(end_station_list))))
            r.expire(key, 2*24*60*60)
            end_station_list = r.get(key)
            if end_station_list:
                return end_station_list
        return end_station_list

    def start_requests(self):
        db_config = settings.get("MONGODB_CONFIG")
        client = MongoClient(db_config["url"])
        self.db = client[db_config["db"]]
        url = "http://www.bus365.com/schedule/departcities/0"
        for city_name in self.city_list:
            req_data = {
                "word": city_name,
                "page": "1",
                "rowCount": "100",
            }
            req_data.update(self.data)
            yield scrapy.Request("%s?%s" % (url, urllib.urlencode(req_data)),
                                 callback=self.parse_start_city,
                                 meta={"start": city_name})

    def parse_start_city(self, response):
        res = json.loads(response.body)
        start = res[0]
        url = "http://%s/schedule/searchscheduler2/0" % start['netname']
#         all_end_station = self.query_all_end_station(start)
#         all_end_station = json.loads(all_end_station)
#         for end in all_end_station:
#             if not self.is_end_city(start, end):
#                 continue
        city_name = start["findname"]
        if len(city_name) > 2 and (city_name.endswith('市') or city_name.endswith('县')):
            city_name = city_name[0:-1]
        for s in self.get_dest_list(start['province'], city_name):
            name, code = s.split("|")
            end = {"city_name": name, "city_code": code}
            today = datetime.date.today()
            for i in range(1, 7):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start["findname"], end['city_name'], sdate):
                    self.logger.info("ignore %s ==> %s %s" % (start["findname"], end['city_name'], sdate))
                    continue
                req_data = {
                    "departdate": sdate,
                    "departcityid": start['id'],
                    "reachstationname": end['city_name']
                }
                req_data.update(self.data)
                yield scrapy.Request("%s?%s" % (url, urllib.urlencode(req_data)),
                                     callback=self.parse_line,
                                     meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["sdate"]
        res = json.loads(response.body)
        self.mark_done(start["findname"], end['city_name'], sdate)
        for d in res['schedules']:
            if int(d['iscansell']) != 1:
                continue
            if float(d['fullprice']) < 11:
                continue
            attrs = dict(
                s_province = start['province'],
                s_city_name = start['findname'],
                s_city_id = start['id'],
                s_city_code= get_pinyin_first_litter(start['findname']),
                s_sta_name= d["busshortname"],
                s_sta_id = d["stationorgid"],
                d_city_name = d["stationname"],
                d_city_code= get_pinyin_first_litter(d["stationname"]),
                d_city_id = d['stationid'],
                d_sta_name = d["stationname"],
                d_sta_id = '',
                drv_date = sdate,
                drv_time = d['departtime'][0:-3],
                drv_datetime = dte.strptime("%s %s" % (sdate, d['departtime'][0:-3]), "%Y-%m-%d %H:%M"),
                distance = d["rundistance"],
                vehicle_type = "",
                seat_type = d['seattype'],
                bus_num = d['schedulecode'],
                full_price = float(d['fullprice']),
                half_price = float(d['fullprice'])/2,
                fee = 3,
                crawl_datetime = dte.now(),
                extra_info = {'start_info':start},
                left_tickets = int(d['residualnumber']),
                crawl_source = "bus365",
                shift_id=d['id'],
            )
            yield LineItem(**attrs)



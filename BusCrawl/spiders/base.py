#!/usr/bin/env python
# encoding: utf-8
import scrapy
import time

from BusCrawl.utils.tool import get_redis
from datetime import datetime as dte
from scrapy.conf import settings
from pymongo import MongoClient


class SpiderBase(scrapy.Spider):
    name = "base"

    def mark_done(self, s_name, d_name, sdate):
        r = get_redis()
        t = time.time()
        k = "%s_%s_%s" % (s_name, d_name, sdate)
        r.hset("line:done:%s" % self.name, k, t)

    def has_done(self, s_name, d_name, sdate):
        r = get_redis()
        k = "%s_%s_%s" % (s_name, d_name, sdate)
        now = time.time()
        t = r.hget("line:done:%s" % self.name, k)
        t = float(t or 0)
        if now - t>12 * 60 * 60:
            return False
        return True

    def __init__(self, province="", city="", *args, **kwargs):
        """
        province: 要爬取的省份, 多个省份用逗号隔开, 为空时不受限制.
        city: 要爬取的城市,多个城市用逗号隔开, 为空时不受限制
        """
        self.province_list = filter(lambda i: i, map(lambda s: s.strip(), province.split(",")))
        self.city_list = filter(lambda i: i, map(lambda s: s.strip(), city.split(",")))
        super(SpiderBase, self).__init__(*args, **kwargs)

    def is_need_crawl(self, province="", city=""):
        """
        eg:
            self.is_need_crawl(province="山东")
            self.is_need_crawl(city="南京")
        """
        if self.province_list and province and province not in self.province_list:
            return False
        if self.city_list and city and city not in self.city_list:
            return False
        return True

    def start_day(self):
        time = dte.now().strftime("%H:%M")
        if time > "15:00":
            return 1        # 从第二天开始爬
        return 0            # 爬当天的

    def get_dest_list(self, province, city, station="", **kwargs):
        """
        获取目的地, 先从数据库获取,为空则去网络找
        """
        self.logger.info("从db获取%s %s %s目的地", province, city, station)
        lst = self.get_dest_list_from_db(province, city, station=station, **kwargs)
        if not lst:
            self.logger.info("从web获取%s %s %s目的地", province, city, station)
            lst = self.get_dest_list_from_web(province, city, **kwargs)
        return lst

    def get_dest_list_from_db(self, province, city, station="", **kwargs):
        """
        从数据库获取目的地
        """
        province, city, station = unicode(province), unicode(city), unicode(station)
        db_config = settings.get("MONGODB_CONFIG")
        client = MongoClient(db_config["url"])
        db = client[db_config["db"]]

        lst = []
        provinces = [province.rstrip("省"), province.rstrip("省") + "省", province]
        citys = [city.rstrip("市").rstrip("区").rstrip("县"), city]
        city_res = db.open_city.find_one({"province": {"$in": provinces}, "city_name": {"$in": citys}})

        temp = {}
        if city_res:
            if station:
                sta_res = db.open_station.find_one({"city": city_res["_id"], "sta_name": station})
                if sta_res:
                    lst = sta_res["dest_info"]
            else:
                for sta_res in db.open_station.find({"city": city_res["_id"]}):
                    for d in sta_res["dest_info"]:
                        if (d["name"], d["dest_id"]) in temp:
                            continue
                        lst.append(d)
                        temp[(d["name"], d["dest_id"])] = 1
        client.close()
        return lst

    def get_dest_list_from_web(self, province, city, **kwargs):
        """
        由子类实现
        """
        pass

    def get_sale_line(self, city=''):
        db_config = settings.get("MONGODB_CONFIG")
        client = MongoClient(db_config["url"])
        db = client[db_config["db"]]
        res = db.open_city.find_one({'city_name': city})
        client.close()
        return res['sale_line']

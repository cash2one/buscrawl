#!/usr/bin/env python
# encoding: utf-8
import scrapy
import time

from BusCrawl.utils.tool import get_redis


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

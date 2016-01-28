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

    def __init__(self, target="", *args, **kwargs):
        self.target = target
        super(SpiderBase, self).__init__(*args, **kwargs)


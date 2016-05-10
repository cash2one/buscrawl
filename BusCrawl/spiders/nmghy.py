#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests
import re
from lxml import etree

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis
from scrapy.conf import settings
from pymongo import MongoClient


class NmghySpider(SpiderBase):
    name = "nmghy"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.NmghyHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
       "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        start_url = "http://www.nmghyjt.com/script/js/dstcity.js"
        yield scrapy.Request(start_url,
                             method="GET",
                             callback=self.parse_target_city)

    def parse_target_city(self, response):
        res = response.body
        matchObj = re.findall(r'XX.module.address.source.fltDomestic = (.*);', res)[0]
        end_list = matchObj[1:-1].split('@')
        line_url = 'http://www.nmghyjt.com/index.php/search/getBuslist'
        start_name = "呼和浩特站"
        for end in end_list:
            if end:
                end_name = end.split("|")[1].decode('utf8')
                end_code = end.split("|")[2]
                today = datetime.date.today()
                for i in range(0, 5):
                    sdate = str(today+datetime.timedelta(days=i))
#                     if self.has_done(start_name, end_name, sdate):
# #                         self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
#                         continue
                    data = {
                        "dd_city": end_name,
                        "dd_code": end_code,
                        "ispost": '1',
                        "orderdate": sdate,
                        "start_city": start_name
                    }
                    yield scrapy.FormRequest(line_url,
                                             method="POST",
                                             formdata=data,
                                             callback=self.parse_line,
                                             meta={"start": start_name, "end": end_name,"end_code":end_code, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        end_code = response.meta["end_code"]
        sdate = response.meta["date"]
        self.mark_done(start, end, sdate)
        content = response.body
        if not isinstance(content, unicode):
            content = content.decode('utf-8')
        sel = etree.HTML(content)
        scheduleList = sel.xpath('//div[@id="visitorDataTable"]/table/tbody/tr')
        if scheduleList:
            for i in scheduleList[1:]:
                bus_num = i.xpath('td[1]/text()')[0]
                start_station = i.xpath('td[2]/text()')[0]
                end_station = i.xpath('td[2]/text()')[0]
                drv_time = i.xpath('td[5]/span[@class="lv_time"]/text()')[0]
                price =  i.xpath('td[8]/span[@class="tk_price"]/text()')[0]
                left_tickets = i.xpath('td[9]/span/text()')[0]
                print i.xpath('td[10]/a/@onclick')[0]
                postdata = i.xpath('td[10]/a/@onclick')[0].split(',')[1][1:-3]
                print end,type(end)
                attrs = dict(
                    s_province = '内蒙古',
                    s_city_name = u"呼和浩特",
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(u"呼和浩特"),
                    s_sta_name = start,
                    s_sta_id = '',
                    d_city_name = end,
                    d_city_code=get_pinyin_first_litter(end),
                    d_city_id = '',
                    d_sta_name = end,
                    d_sta_id = end_code,
                    drv_date = sdate,
                    drv_time = drv_time,
                    drv_datetime = dte.strptime("%s %s" % (sdate, drv_time), "%Y-%m-%d %H:%M"),
                    distance = "0",
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = bus_num,
                    full_price = float(price),
                    half_price = float(price)/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {"postdata": postdata},
                    left_tickets = int(left_tickets),
                    crawl_source = "nmghy",
                    shift_id="",
                )
                yield LineItem(**attrs)


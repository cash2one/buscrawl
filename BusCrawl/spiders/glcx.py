#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib
from bs4 import BeautifulSoup as bs
import re
# from fabric.colors import green, red
from cchardet import detect
from scrapy.shell import inspect_response

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter, vcode_zhw
from base import SpiderBase
from scrapy.conf import settings
from pymongo import MongoClient
import requests
from pprint import pprint
# import cStringIO
# from PIL import Image
# import ipdb

db_config = settings.get("MONGODB_CONFIG")
city = MongoClient(db_config["url"])[db_config["db"]]['glcxcity']


class Glcx(SpiderBase):
    name = "glcx"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            # 'BusCrawl.middleware.TongChengHeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.1,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    # dcitys = city.find({'start_id': {'$exists': True}}).batch_size(16)
    url = 'http://www.0000369.cn/buytks!searchtks.action'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def start_requests(self):
        days = 7
        today = datetime.date.today()
        d = {
            u'济南长途汽车总站': '1',
            u'济南长途汽车总站南区': '2',
            u'济南长途汽车东站': '3',
            u'章丘长途汽车总站': '4',
        }
        for x in city.find().batch_size(16):
            for y in xrange(self.start_day(), days):
                for z in d:
                    # if z != 'C1K001-102017' or x.get('szCode') != '广州东站':
                    #     continue
                    start_id = d[z]
                    end_id = x.get('end_id')
                    sdate = str(today + datetime.timedelta(days=y))
                    data = {
                        'stationId': start_id,
                        'portId': end_id,
                        'startTime': sdate,
                    }
                    # print data
                    if self.has_done(z, x['end'], sdate):
                        continue
                    yield scrapy.Request(
                        url=self.url,
                        callback=self.parse_line,
                        method='POST',
                        body=urllib.urlencode(data),
                        headers=self.headers,
                        meta={
                            's_city_name': '济南',
                            'start_id': start_id,
                            'start': z,
                            'end_id': end_id,
                            'end': x['end'],
                            'sdate': sdate,
                        },
                    )

        # 初始化抵达城市
        # url = 'http://www.0000369.cn/buytks!list.action'
        # yield scrapy.Request(url, callback=self.parse_dcity, meta={'s_city_name': '济南'})

    # 初始化到达城市
    def parse_dcity(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        soup = bs(response.body, 'lxml')
        info = soup.find_all('script', attrs={'src': False})[2]
        info = str(info).split()
        data = {'s_city_name': s_city_name}
        for x in info:
            try:
                tmp = x.split("'")
                data['end'] = tmp[1].decode('utf-8')
                data['end_id'] = tmp[-2]
                # print len(tmp)
                if len(tmp) != 7:
                    continue
                if city.find({'end': data['end']}).count() <= 0:
                    city.save(dict(data))
            except:
                pass

    def parse_line(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        start = response.meta['start']
        end = response.meta['end']
        start_id = response.meta['start_id'].decode('utf-8')
        end_id = response.meta['end_id'].decode('utf-8')
        sdate = response.meta['sdate'].decode('utf-8')
        self.mark_done(start, end, sdate)
        soup = bs(response.body, 'lxml')
        info = soup.find('table', attrs={'id': 'selbuy'})
        items = info.find_all('tr', attrs={'class': True})
        if len(items) == 0:
            return
        # inspect_response(response, self)
        for x in items:
            try:
                y = x.find_all('td')
                bus_num = y[0].get_text().strip()
                drv_date = sdate
                drv_time = y[1].get_text().strip()
                d_sta_name = y[3].get_text().strip().decode('utf-8')
                vehicle_type = y[4].get_text().strip().decode('utf-8')
                full_price = y[6].get_text().strip()
                extra = y[7].get_text().strip()
                left_tickets = y[10].get_text().strip()
                extra = {'startNo': y[11].get_text().strip()}
                attrs = dict(
                    s_province='山东',
                    s_city_id="",
                    s_city_name=s_city_name,
                    s_sta_name=start,
                    s_city_code=get_pinyin_first_litter(s_city_name),
                    s_sta_id=start_id,
                    d_city_name=d_sta_name,
                    d_city_id='',
                    d_city_code=get_pinyin_first_litter(d_sta_name),
                    d_sta_id=end_id,
                    d_sta_name=d_sta_name,
                    drv_date=drv_date,
                    drv_time=drv_time,
                    drv_datetime=dte.strptime("%s %s" % (
                        drv_date, drv_time), "%Y-%m-%d %H:%M"),
                    distance='',
                    vehicle_type=vehicle_type,
                    seat_type="",
                    bus_num=bus_num,
                    full_price=float(full_price),
                    half_price=float(full_price) / 2,
                    fee=0.0,
                    crawl_datetime=dte.now(),
                    extra_info=extra,
                    left_tickets=int(left_tickets),
                    crawl_source="glcx",
                    shift_id="",
                )
                if end == d_sta_name and int(left_tickets):
                    yield LineItem(**attrs)

            except:
                pass

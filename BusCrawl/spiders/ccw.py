#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib
from bs4 import BeautifulSoup as bs
import re
# from fabric.colors import green, red
# from cchardet import detect
from scrapy.shell import inspect_response

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase
from scrapy.conf import settings
from pymongo import MongoClient
# import ipdb

db_config = settings.get("MONGODB_CONFIG")
city = MongoClient(db_config["url"])[db_config["db"]]['ccwcity']


class Ccw(SpiderBase):
    name = "ccw"
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
        "DOWNLOAD_DELAY": 0.25,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    dcitys = city.find({'s_city_name': {'$exists': True}, 'd_city_name': {
        '$exists': True}})
    base_url = "http://order.xuyunjt.com/wsdgbccx.aspx"
    # base_url = 'http://www.hn96520.com/ajax/query.aspx?method=GetListByPY&q=b&limit=20&timestamp=1465204637302&global=410101'
    # base_url = 'http://www.hn96520.com/placeorder.aspx?start=%E9%83%91%E5%B7%9E%E4%B8%AD%E5%BF%83%E7%AB%99&global=410101&end=%E6%9D%AD%E5%B7%9E&date=2016-05-30'

    def start_requests(self):
        days = 7
        today = datetime.date.today()
        for x in self.dcitys:
            for y in xrange(self.start_day(), days):
                start = x.get('start')
                end = x.get('mc')
                sdate = str(today + datetime.timedelta(days=y))
                if self.has_done(start, end, sdate):
                    continue
                url = 'http://www.chechuw.com/qiche/QTDemo/CARInfoSelect.aspx?chufashijian={0}&chufadi={1}'.format(
                    sdate, x.get('d_city_name'))
                # print url, x.get('scity')
                yield scrapy.Request(url, callback=self.parse_line,
                                     meta={'d_city_name': x.get('d_city_name'), 's_city_name': x.get('s_city_name'),
                                           'sdate': sdate})

        # 初始化抵达城市
        # dcitys = 'abcdefghijklmnopqrstuvwxyz'
        # for dcity in dcitys:
        #     url = 'http://www.chechuw.com/qiche/Handlers/GetIntentStation.ashx?term={0}'.format(dcity)
        #     yield scrapy.Request(url, callback=self.parse_dcity)

    # 初始化到达城市
    def parse_dcity(self, response):
        data = {}
        s_city_name = '宿迁市'
        data['s_city_name'] = s_city_name
        soup = json.loads(response.body)
        for x in soup:
            try:
                data['d_city_name'] = x.get('label', '')
                if city.find({'s_city_name': data['s_city_name'], 'd_city_name': data['d_city_name']}).count() <= 0:
                    city.save(dict(data))
            except:
                pass

    def parse_line(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        d_city_name = response.meta['d_city_name'].decode('utf-8')
        # sdate = response.meta['sdate'].decode('utf-8')
        # self.mark_done(s_city_name, d_city_name, sdate)
        soup = bs(response.body, 'lxml')
        # inspect_response(response, self)
        try:
            info = soup.find('table', attrs={'class': 'sub-timeBody'}).find_all('tr')
        except:
            info = []
        for x in info:
            try:
                d_city_name = x.find_all('td')[0].get_text().strip()
                drv_date = x.find_all('td')[1].get_text().strip()
                drv_time = x.find_all('td')[2].get_text().strip()
                vehicle_type = x.find_all('td')[3].get_text().strip()
                full_price = x.find_all('td')[4].get_text().strip()
                left_tickets = x.find_all('td')[5].get_text().strip()
                drv_datetime = dte.strptime("%s %s" % (drv_date, drv_time), "%Y%m%d %H%M")
                extra = x.find_all('td')[6].find('img').get('onclick').split('?')[-1]
                extra = urllib.unquote(extra)
                extra_info = {}
                for y in extra.split('&'):
                    extra_info[y.split('=')[0]] = y.split('=')[1]
                # print extra_info
                # print d_city_name, s_city_name, drv_date, drv_time, vehicle_type, full_price, left_tickets, drv_datetime

                attrs = dict(
                    s_province='江苏省',
                    s_city_id="",
                    s_city_name=s_city_name,
                    s_sta_name=s_city_name,
                    s_city_code=get_pinyin_first_litter(s_city_name),
                    s_sta_id='',
                    d_city_name=d_city_name,
                    d_city_id="",
                    d_city_code=get_pinyin_first_litter(d_city_name),
                    d_sta_id="",
                    d_sta_name=d_city_name,
                    drv_date=drv_date,
                    drv_time=drv_time,
                    drv_datetime=drv_datetime,
                    distance='',
                    vehicle_type=vehicle_type,
                    seat_type="",
                    bus_num=extra_info.get('bcbm', ''),
                    full_price=float(full_price),
                    half_price=float(full_price) / 2,
                    fee=0.0,
                    crawl_datetime=dte.now(),
                    extra_info=extra_info,
                    left_tickets=left_tickets,
                    crawl_source="ccw",
                    shift_id="",
                )
                # print(attrs)
                yield LineItem(**attrs)

            except:
                pass

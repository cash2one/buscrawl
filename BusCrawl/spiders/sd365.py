# !/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib
from bs4 import BeautifulSoup as bs
import re
# from fabric.colors import green, red
# from cchardet import detect
# from scrapy.shell import inspect_response

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase
from scrapy.conf import settings
from pymongo import MongoClient
import requests
from pprint import pprint
# import cStringIO
# from PIL import Image
# import ipdb
# from seleniumrequests import PhantomJS

db_config = settings.get("MONGODB_CONFIG")
city = MongoClient(db_config["url"])[db_config["db"]]['sd365city']

class Sd365(SpiderBase):
    name = "sd365"
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    dcitys = city.find()

    def get_fromid(self):
        url = 'http://www.36565.cn/js/data/buscityjs.js'
        r = requests.get(url)
        info = r.json().values()[0].split('@')
        res = {}
        for x in info:
            try:
                y = x.split('|')
                res[y[1]] = y[2]
            except:
                pass
        return res
    def get_pre(self, url):
        r = requests.get(url, headers=self.headers)
        try:
            code = r.content.split('code:')[-1].split()[0].split('"')[1]
        except:
            code = ''
        soup = bs(r.content, 'lxml')
        info = soup.find_all('input', attrs={'class': 'filertctrl', 'name': 'siids'})
        sids = ''
        for x in info:
            sids += x['value'] + ','
        if code and sids:
            return code, sids

    def start_requests(self):
        days = 3
        today = datetime.date.today()
        data = {
            'a': 'getlinebysearch',
            'c': 'tkt3',
            'toid': '',
            'type': '0',
        }
        if self.city_list:
            self.dcitys = city.find({'s_city_name': {'$in': self.city_list}})
        #self.dcitys = city.find({'s_city_name': '烟台市'})
        for x in self.dcitys:
            for y in xrange(self.start_day(), days):  # self.start_day()
                start = x.get('s_city_name')
                # if start == '济宁市':
                #     continue
                end = x.get('d_city_name')
                # fromid = x.get('fromid')
                # toid = x.get('toid')
                sdate = str(today + datetime.timedelta(days=y))
                if self.has_done(start, end, sdate):
                    continue
                url = 'http://www.36565.cn/?c=tkt3&a=search&fromid=&from={0}&toid=&to={1}&date={2}&time=0#'.format(start, end, sdate)
                print url
                res = self.get_pre(url)
                if not res:
                    continue
                print url, res
                data['code'] = res[0]
                data['date'] = sdate
                data['sids'] = res[1][:-1]
                data['to'] = end
                last_url = 'http://www.36565.cn/?' + urllib.urlencode(data)
                yield scrapy.Request(
                  url=last_url,
                  callback=self.parse_line,
                  method='GET',
                  headers=self.headers,
                  meta={
                      'start': start,
                      'end': end,
                      'sdate': sdate,
                      'last_url': last_url,
                  },
                )

        # 初始化抵达城市
        # res = self.get_fromid()
        # for x in res.items():
        #     url = 'http://www.36565.cn/js/data/cityport_{0}.js'.format(x[1])
        #     yield scrapy.Request(url, callback=self.parse_dcity, meta={'s_city_name': x[0], 'fromid': x[1]})

    # 初始化到达城市
    def parse_dcity(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        fromid = response.meta['fromid'].decode('utf-8')
        print s_city_name
        info = response.body.split('[]')[2].split(';')
        data = {'s_city_name': s_city_name, 'fromid': fromid}
        for x in info:
            print x
            try:
                y = x.split('=')[1].split(',')
                data['d_city_name'] = y[1].split("'")[1]
                data['toid'] = y[0].split("'")[1]
                if city.find({'s_city_name': data['s_city_name'], 'd_city_name': data['d_city_name'], 'toid': data['toid']}).count() <= 0:
                    city.save(dict(data))
            except:
                pass

    def parse_line(self, response):
        start = response.meta['start'].decode('utf-8')
        end = response.meta['end'].decode('utf-8')
        sdate = response.meta['sdate'].decode('utf-8')
        last_url = response.meta['last_url']
        print start, end, sdate
        self.mark_done(start, end, sdate)
        soup = json.loads(response.body)
        for x in soup:
            try:
                drv_date = x['bpnDate']
                drv_time = x['bpnSendTime']
                s_sta_name = x['shifazhan']
                s_sta_id = x['siID']
                d_sta_name = x['daozhan']
                # d_sta_name = x['bpnSendPort']
                left_tickets = x['bpnLeftNum']
                vehicle_type = x['btpName']
                extra = {
                    'sid': x['siID'],
                    'dpid': x['prtID'],
                    'l': x['bliID'],
                    't': x['bpnDate'],
                    'last_url': last_url,
                }
                bus_num = x['bliID']
                full_price = x['prcPrice']
                attrs = dict(
                    s_province='山东',
                    s_city_id="",
                    s_city_name=start,
                    s_sta_name=s_sta_name,
                    s_city_code=get_pinyin_first_litter(start),
                    s_sta_id=s_sta_id,
                    d_city_name=end,
                    d_city_id="",
                    d_city_code=get_pinyin_first_litter(end),
                    d_sta_id="",
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
                    crawl_source="sd365",
                    shift_id="",
                )
                # pprint(attrs)
                if int(left_tickets):
                    yield LineItem(**attrs)

            except:
                print soup
                pass

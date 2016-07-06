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
# from scrapy.shell import inspect_response

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
city = MongoClient(db_config["url"])[db_config["db"]]['zhwcity']


class Zhw(SpiderBase):
    name = "zhw"
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

    dcitys = city.find({'szCode': {'$exists': True}}).batch_size(30)
    url = 'http://www.zhwsbs.gov.cn:9013/shfw/zaotsTicket/pageLists.xhtml'
    # base_url = 'http://www.hn96520.com/ajax/query.aspx?method=GetListByPY&q=b&limit=20&timestamp=1465204637302&global=410101'
    # base_url = 'http://www.hn96520.com/placeorder.aspx?start=%E9%83%91%E5%B7%9E%E4%B8%AD%E5%BF%83%E7%AB%99&global=410101&end=%E6%9D%AD%E5%B7%9E&date=2016-05-30'

    def update_cookies(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'http://www.zhwsbs.gov.cn:9013/shfw/zaotsTicket/pageLists.xhtml',
        }
        data = {
            'SchDate': '',
            'SchTime': '',
            'checkCode': '',
            'StartStation': '"-"',
            'SchDstNodeName': '',
        }
        today = datetime.date.today()
        sdate = str(today + datetime.timedelta(days=1))
        for x in xrange(5):
            code, cookies = vcode_zhw()
            data['SchDstNodeName'] ='广东东站'
            data['SchDate'] = sdate
            data['checkCode'] = code
            r = requests.post(self.url, headers=headers, cookies=cookies, data=data)
            soup = bs(r.content, 'lxml')
            info = soup.find('table', attrs={'id': 'changecolor'})
            if '验证码错误' not in info.get_text():
                return (code, cookies)
            else:
                print info.get_text()

    def start_requests(self):
        days = 7
        today = datetime.date.today()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'http://www.zhwsbs.gov.cn:9013/shfw/zaotsTicket/pageLists.xhtml',
        }
        data = {
            'SchDate': '',
            'SchTime': '',
            'checkCode': '',
            'StartStation': '"-"',
            'SchDstNodeName': '',
        }
        l = ['C1K001-102017', 'C1K027-102018', 'C1K013-102019', 'C1K030-102023', 'C2K003-102027', 'C2K001-102028', 'C1K006-102030', 'C1K004-102031', 'C1K007-102032', 'C1K008-102033', 'TJZ001-102020', 'JDZ001-102021', 'GBPW01-102024', 'XPZ001-102029']
        code, cookies = self.update_cookies()
        for x in city.find({'szCode': {'$exists': True}}).batch_size(10):
            for y in xrange(self.start_day(), days):
                for z in l:
                    # if z != 'C1K001-102017' or x.get('szCode') != '广州东站':
                    #     continue
                    start = x.get('city_name')
                    end = x.get('szCode')
                    sdate = str(today + datetime.timedelta(days=y))
                    if self.has_done(start, end, sdate):
                        continue
                    data['SchDstNodeName'] = end
                    data['SchDate'] = sdate
                    data['checkCode'] = code
                    data['StartStation'] = z
                    yield scrapy.Request(
                        url=self.url,
                        callback=self.parse_line,
                        method='POST',
                        body=urllib.urlencode(data),
                        headers=headers,
                        cookies=dict(cookies),
                        meta={
                            's_city_name': '珠海',
                            'start': start,
                            'end': end,
                            'sdate': sdate,
                        },
                    )

        # 初始化抵达城市
        # letter = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        # for x in letter:
        #     url = 'http://www.zhwsbs.gov.cn:9013/shfw/zaotsTicket/findCity.xhtml?term={0}%2520%2520&featureClass=P&style=full&maxRows=8&name_startsWith={1}++'.format(x, x)
        #     yield scrapy.Request(self.url, callback=self.parse_dcity,meta={'s_city_name': '珠海'})

    # 初始化到达城市
    def parse_dcity(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        soup = json.loads(response.body)
        for data in soup:
            data['city_name'] = s_city_name
            if city.find({'szCode': data['szCode'], 'zmCode': data['zmCode'], 'sname': data['sname']}).count() <= 0:
                city.save(dict(data))

    def parse_line(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        start = response.meta['start'].decode('utf-8')
        end = response.meta['end'].decode('utf-8')
        sdate = response.meta['sdate'].decode('utf-8')
        self.mark_done(start, end, sdate)
        soup = bs(response.body, 'lxml')
        info = soup.find('table', attrs={'id': 'changecolor'})
        items = info.find_all('tr', attrs={'id': True})
        for i, x in enumerate(items):
            i = i + 1
            try:
                y = x.find_all('td')
                sts = x.find('input', attrs={'disabled': 'disabled'})
                drv_date = y[0].get_text().strip()
                drv_time = y[1].get_text().strip()
                s_sta_name = y[2].get_text().strip()
                d_sta_name = y[3].get_text().strip()
                left_tickets = y[5].get_text().strip()
                vehicle_type = y[6].get_text().strip()
                extra = {}
                extra['txtSginData'] = info.find('input', attrs={'id': 'HI-SginData-{0}'.format(i)}).get('value', '')
                extra['ctm'] = info.find('input', attrs={'id': 'HI-ctm-{0}'.format(i)}).get('value', '')
                extra['txtSchStationName'] = info.find('input', attrs={'id': 'HI-SchStationName-{0}'.format(i)}).get('value', '')
                # extra['txtSchWaitStName'] = info.find('input', attrs={'id': 'HI-SchWaitStCode-{0}'.format(i)}).get('value', '')
                extra['txtSchDstNode'] = info.find('input', attrs={'id': 'HI-SchDstNode-{0}'.format(i)}).get('value', '')
                extra['txtSchWaitingRoom'] = info.find('input', attrs={'id': 'HI-SchWaitingRoom-{0}'.format(i)}).get('value', '')
                extra['txtSchPrice'] = info.find('input', attrs={'id': 'HI-SchPri-{0}'.format(i)}).get('value', '')
                extra['txtSchLocalCode'] = info.find('input', attrs={'id': 'HI-SchLocalCode-{0}'.format(i)}).get('value', '')
                extra['txtSchWaitStCode'] = info.find('input', attrs={'id': 'HI-SchWaitStCode-{0}'.format(i)}).get('value', '')
                attrs = dict(
                    s_province='广东',
                    s_city_id="",
                    s_city_name=s_city_name,
                    s_sta_name=s_sta_name,
                    s_city_code=get_pinyin_first_litter(s_city_name),
                    s_sta_id='',
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
                    bus_num='',
                    full_price=float(extra['txtSchPrice']),
                    half_price=float(extra['txtSchPrice']) / 2,
                    fee=0.0,
                    crawl_datetime=dte.now(),
                    extra_info=extra,
                    left_tickets=int(left_tickets),
                    crawl_source="zhw",
                    shift_id="",
                )
                # pprint(attrs)
                if not sts:
                    yield LineItem(**attrs)

            except:
                pass

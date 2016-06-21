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
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase
from scrapy.conf import settings
from pymongo import MongoClient
# import ipdb

db_config = settings.get("MONGODB_CONFIG")
city = MongoClient(db_config["url"])[db_config["db"]]['xyjtcity']


class Xyjt(SpiderBase):
    name = "xyjt"
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

    dcitys = city.find({'start': {'$exists': True}, 'end': {
        '$exists': True}, 'start_code': {'$exists': True}})
    base_url = "http://order.xuyunjt.com/wsdgbccx.aspx"
    # base_url = 'http://www.hn96520.com/ajax/query.aspx?method=GetListByPY&q=b&limit=20&timestamp=1465204637302&global=410101'
    # base_url = 'http://www.hn96520.com/placeorder.aspx?start=%E9%83%91%E5%B7%9E%E4%B8%AD%E5%BF%83%E7%AB%99&global=410101&end=%E6%9D%AD%E5%B7%9E&date=2016-05-30'

    def start_requests(self):
        days = 7
        today = datetime.date.today()
        if self.city_list:
            self.dcitys = city.find({'s_city_name': {'$in': self.city_list}})
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'X-MicrosoftAjax': 'Delta=true',
        }
        for x in self.dcitys:
            for y in xrange(self.start_day(), days):
                start = x.get('start')
                end = x.get('end')
                start_code = x.get('start_code')
                sdate = str(today + datetime.timedelta(days=y))
                if self.has_done(start, end, sdate):
                    continue
                url = 'http://order.xuyunjt.com/wsdgbccx.aspx'
                ste = sdate.replace('-', '')
                pa = '''
                ctl00$ContentPlaceHolder1$ScriptManager1=ctl00$ContentPlaceHolder1$ScriptManager1|ctl00$ContentPlaceHolder1$BtnBccx&__EVENTTARGET=&__EVENTARGUMENT=&__LASTFOCUS=&__VIEWSTATE=%2FwEPDwUKLTUzNTg5Njk5OA9kFgJmD2QWAgIDD2QWAgIHD2QWBgIFDxBkZBYBZmQCCQ8QDxYGHg1EYXRhVGV4dEZpZWxkBQlzYWxlX2RhdGUeDkRhdGFWYWx1ZUZpZWxkBQlzYWxlX2RhdGUeC18hRGF0YUJvdW5kZ2QQFRIIMjAxNjA2MTMIMjAxNjA2MTQIMjAxNjA2MTUIMjAxNjA2MTYIMjAxNjA2MTcIMjAxNjA2MTgIMjAxNjA2MTkIMjAxNjA2MjAIMjAxNjA2MjEIMjAxNjA2MjIIMjAxNjA2MjMIMjAxNjA2MjQIMjAxNjA2MjUIMjAxNjA2MjYIMjAxNjA2MjcIMjAxNjA2MjgIMjAxNjA2MjkIMjAxNjA2MzAVEggyMDE2MDYxMwgyMDE2MDYxNAgyMDE2MDYxNQgyMDE2MDYxNggyMDE2MDYxNwgyMDE2MDYxOAgyMDE2MDYxOQgyMDE2MDYyMAgyMDE2MDYyMQgyMDE2MDYyMggyMDE2MDYyMwgyMDE2MDYyNAgyMDE2MDYyNQgyMDE2MDYyNggyMDE2MDYyNwgyMDE2MDYyOAgyMDE2MDYyOQgyMDE2MDYzMBQrAxJnZ2dnZ2dnZ2dnZ2dnZ2dnZ2dkZAIVD2QWAmYPZBYCAgEPPCsADQBkGAEFIGN0bDAwJENvbnRlbnRQbGFjZUhvbGRlcjEkR1ZCY2N4D2dkkseqxdZHcjzmn1bUQclXbCaNhlk%3D&ctl00$ContentPlaceHolder1$ddlincounty={0}&ctl00$ContentPlaceHolder1$ddlsaledate={1}&ctl00$ContentPlaceHolder1$txtstop={2}&radio={3}&ctl00$ContentPlaceHolder1$BtnBccx=%E7%8F%AD%E6%AC%A1%E6%9F%A5%E8%AF%A2
                '''.format(start_code, ste, end, end)
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_line,
                    method='POST',
                    body=pa,
                    headers=headers,
                    meta={
                        's_city_name': '徐州市',
                        'start': start,
                        'end': end,
                        'sdate': sdate,
                    },
                )

        # 初始    化抵达城市
        # yield scrapy.Request(self.base_url, callback=self.parse_dcity,
        # meta={'s_city_name': '徐州市'})

    # 初始化到达城市
    def parse_dcity(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        soup = bs(response.body, 'lxml')
        data = {}
        # inspect_response(response, self)
        data['s_city_name'] = s_city_name
        snames = []
        dnames = []
        info = soup.find('select', attrs={
                         'name': 'ctl00$ContentPlaceHolder1$ddlincounty'}).find_all('option')
        snames = [(x.get_text(), x.get('value')) for x in info]
        info = soup.find(
            'td', attrs={'colspan': '3', 'align': 'center'}).find_all('label')
        dnames = [x.get_text() for x in info]

        print snames, dnames
        for x in snames:
            for y in dnames:
                data['start'] = x[0]
                data['start_code'] = x[1]
                data['end'] = y
                if city.find({'start': data['start'], 'end': data['end'], 'start_code': data['start_code']}).count() <= 0:
                    city.save(dict(data))

    def parse_line(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        start = response.meta['start'].decode('utf-8')
        end = response.meta['end'].decode('utf-8')
        sdate = response.meta['sdate'].decode('utf-8')
        self.mark_done(start, end, sdate)
        # inspect_response(response, self)
        soup = bs(response.body, 'lxml')
        # print soup
        info = soup.find('table', attrs={'id': 'ctl00_ContentPlaceHolder1_GVBccx'}).find_all(
            'tr', attrs={'class': True})
        for x in info[1:]:
            try:
                y = x.find_all('td')
                drv_date = y[0].get_text().strip()
                s_sta_name = y[1].get_text().strip()
                bus_num = y[2].get_text().strip()
                d_city_name = y[3].get_text().strip()
                # d_sta_name = y[4].get_text().strip()
                drv_time = y[5].get_text().strip()
                full_price = y[6].get_text().strip()
                half_price = y[7].get_text().strip()
                left_tickets = y[8].get_text().strip()
                vehicle_type = y[10].get_text().strip()
                distance = y[11].get_text().strip()
                extra = y[12].a.get('href').strip().split('?')[-1]
                extra = urllib.unquote(extra)
                extra_info = {}
                for z in extra.split('&'):
                    extra_info[z.split('=')[0]] = z.split('=')[1]
                attrs = dict(
                    s_province='江苏省',
                    s_city_id="",
                    s_city_name=s_city_name,
                    s_sta_name=s_sta_name,
                    s_city_code=get_pinyin_first_litter(s_city_name),
                    s_sta_id='',
                    d_city_name=d_city_name,
                    d_city_id="",
                    d_city_code=get_pinyin_first_litter(d_city_name),
                    d_sta_id="",
                    d_sta_name=d_city_name,
                    drv_date=drv_date,
                    drv_time=drv_time,
                    drv_datetime=dte.strptime("%s %s" % (
                        drv_date, drv_time), "%Y-%m-%d %H:%M"),
                    distance=unicode(distance),
                    vehicle_type=vehicle_type,
                    seat_type="",
                    bus_num=bus_num,
                    full_price=float(full_price),
                    half_price=float(half_price),
                    fee=0.0,
                    crawl_datetime=dte.now(),
                    extra_info=extra_info,
                    left_tickets=left_tickets,
                    crawl_source="xyjt",
                    shift_id="",
                )
                # print attrs
                yield LineItem(**attrs)

            except:
                pass

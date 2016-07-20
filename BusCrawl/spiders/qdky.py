#!/usr/bin/env python
# encoding: utf-8

import scrapy
# import json
import datetime
import urllib
from bs4 import BeautifulSoup as bs
import re

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase
from scrapy.conf import settings
from pymongo import MongoClient
import requests
# import cStringIO
# from PIL import Image
# import ipdb

db_config = settings.get("MONGODB_CONFIG")
city = MongoClient(db_config["url"])[db_config["db"]]['qdkycity']


class Qdky(SpiderBase):
    name = "qdky"
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
    url = 'http://ticket.qdjyjt.com/'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def update_state(self):
        r = requests.get(self.url, headers=self.headers)
        print r.ok
        soup = bs(r.content, 'lxml')
        state = soup.find('input', attrs={'id': '__VIEWSTATE'}).get('value', '')
        valid = soup.find('input', attrs={'id': '__EVENTVALIDATION'}).get('value', '')
        print len(state)
        if state and valid and r.ok:
            return (state, valid, dict(r.cookies))

    def start_requests(self):
        days = 7
        today = datetime.date.today()
        sta_info = {
            '1': '1.青岛站    ',
            '2': '2.沧口汽车站',
            '3': '3.青岛西站  ',
            '4': 'B.青岛北站  ',
            '5': 'C.青岛海泊河',
            '6': 'D.青岛东站  ',
            '7': 'F.利津路站  ',
            '8': 'A.黄岛开发区',
            '9': '5.胶州汽车站',
            '10': '8.胶南汽车站',
            '11': '4.即墨汽车站',
            '12': '7.莱西汽车站',
            '13': '9.平度汽车站',
            '14': 'E.华联火车站',
        }
        data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': '',
            '__EVENTVALIDATION': '',
            'ctl00$ContentPlaceHolder1$DropDownList3': '',
            'ctl00$ContentPlaceHolder1$chengchezhan_id': '',
            'destination-id': '',
            'ctl00$ContentPlaceHolder1$mudizhan_id': '',
            'tripDate': '',
            'ctl00$ContentPlaceHolder1$chengcheriqi_id': '',
            'ctl00$ContentPlaceHolder1$chengcheriqi_id0': '',
            'ctl00$ContentPlaceHolder1$Button_1_cx': '车次查询',

        }

        for x in city.find({'end': {'$exists': True}}).batch_size(16):
            for y in xrange(self.start_day(), days):
                for z in sta_info.values():
                    start = z.split('.')[-1]
                    end = x['end']
                    if '安庆' not in end:
                        continue
                    state, valid, cookies = self.update_state()
                    end_id = x.get('end_id')
                    sdate = str(today + datetime.timedelta(days=y))
                    data['__VIEWSTATE'] = state
                    data['__EVENTVALIDATION'] = valid
                    data['ctl00$ContentPlaceHolder1$DropDownList3'] = z
                    data['destination-id'] = end_id
                    print start, end
                    # if self.has_done(start, end, sdate):
                    #     continue
                    yield scrapy.Request(
                        url=self.url,
                        callback=self.parse_line,
                        method='POST',
                        body=urllib.urlencode(data),
                        headers=self.headers,
                        cookies=cookies,
                        meta={
                            'start': start,
                            'end': end,
                            'sdate': sdate,
                        },
                    )

        # 初始化抵达城市
        # url = 'http://ticket.qdjyjt.com/Scripts/destination.js'
        # yield scrapy.Request(url, callback=self.parse_dcity, meta={'s_city_name': '青岛'})

    # 初始化到达城市
    def parse_dcity(self, response):
        s_city_name = response.meta['s_city_name'].decode('utf-8')
        soup = response.body.split('[')[-1].split(']')[0]
        info = soup.split('}')
        data = {'s_city_name': s_city_name}
        for x in info:
            try:
                tmp = x.split("'")
                data['end'] = tmp[-2].decode('utf-8')
                data['end_id'] = tmp[1]
                print data['end'], data['end_id']
                if len(tmp) != 5:
                    continue
                if city.find({'end': data['end']}).count() <= 0:
                    city.save(dict(data))
            except:
                pass

    def parse_line(self, response):
        start = response.meta['start']
        end = response.meta['end']
        sdate = response.meta['sdate'].decode('utf-8')
        self.mark_done(start, end, sdate)
        soup = bs(response.body, 'lxml')
        info = soup.find('table', attrs={'id': 'ContentPlaceHolder1_GridViewbc'})
        print info
        items = info.find_all('tr', attrs={'class': True})
        if len(items) == 0:
            return
        # inspect_response(response, self)
        for x in items:
            try:
                print x
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
                    s_city_name='青岛',
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

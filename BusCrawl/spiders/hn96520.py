#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib
from bs4 import BeautifulSoup as bs
import re
# from fabric.colors import green, red


from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase


class HnSpider(SpiderBase):
    name = "hn96520"
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
        "DOWNLOAD_DELAY": 0.75,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    base_url = "http://www.hn96520.com/default.aspx"
    #base_url = 'http://www.hn96520.com/placeorder.aspx?start=%E9%83%91%E5%B7%9E%E4%B8%AD%E5%BF%83%E7%AB%99&global=410101&end=%E6%9D%AD%E5%B7%9E&date=2016-05-30'

    def start_requests(self):
        yield scrapy.Request(self.base_url, callback=self.parse)

    def parse(self, response):
        soup = bs(response.body, 'lxml')
        info = soup.find_all(
            'div', attrs={'id': re.compile(r"divHotline\_\d+")})
        # print(info)
        urls = []
        qtimes = []
        for x in info:
            try:
                y = x.find_all('a')
                for z in y:
                    url = 'http://www.hn96520.com/' + z.get('href')
                    urls.append(url.strip())
            except Exception as e:
                print(e)
        urls = list(set(urls))
        # print(red(len(urls)))
        for i in xrange(7):
            qtime = (datetime.datetime.now() +
                     datetime.timedelta(i)).strftime("%Y-%m-%d")
            qtimes.append(qtime)
        # print(qtimes)
        for j in qtimes:
            for k in urls:
                url = k[:-10] + j
                yield scrapy.Request(url, callback=self.parse_line)

    def parse_line(self, response):
        # from pprint import pprint
        # print(green('Staring {0}'.format(response.url)))
        soup = bs(response.body, 'lxml')
        info = soup.find('table', attrs={'class': 'resulttb'}).find_all(
            'tbody', attrs={'class': 'rebody'})
        for x in info:
            try:
                bus_num = x.find(
                    'td', attrs={'align': 'center'}).get_text().strip()
                s_province = x.find_all(
                    'td')[1].get_text().split()[0]
                d_city_name = x.find_all('td')[1].get_text().split()[1]
                drv_date = x.find_all('td')[2].get_text().strip()
                drv_time = x.find_all('td')[3].get_text().strip()
                d_sta_name = x.find_all('td')[4].get_text().strip()
                distance = x.find_all('td')[5].get_text().strip()
                vehicle_type = x.find_all('td')[6].get_text().strip()
                full_price = x.find_all('td')[7].get_text().strip()
                left_tickets = int(x.find_all('td')[8].get_text().strip())
                y = x.find_all('td')[9].a.get('href').split('?')[-1]
                extra  = {}
                for z in y.split('&'):
                    extra[z.split('=')[0]] = z.split('=')[1]

                attrs = dict(
                    s_province='河南',
                    s_city_id="",
                    s_city_name=s_province,
                    s_sta_name=s_province,
                    s_city_code=get_pinyin_first_litter(s_province),
                    s_sta_id='',
                    d_city_name=d_city_name,
                    d_city_id="",
                    d_city_code=get_pinyin_first_litter(d_city_name),
                    d_sta_id="",
                    d_sta_name=d_sta_name,
                    drv_date=drv_date,
                    drv_time=drv_time,
                    drv_datetime=dte.strptime("%s %s" % (
                        drv_date, drv_time), "%Y-%m-%d %H:%M"),
                    distance=unicode(distance),
                    vehicle_type=vehicle_type,
                    seat_type="",
                    bus_num=bus_num,
                    full_price=float(full_price),
                    half_price=float(full_price) / 2,
                    fee=0.0,
                    crawl_datetime=dte.now(),
                    extra_info=extra,
                    left_tickets=left_tickets,
                    crawl_source="hn96520",
                    shift_id="",
                )
                # pprint(attrs)
                yield LineItem(**attrs)

            except Exception as e:
                print(e)

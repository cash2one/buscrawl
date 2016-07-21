#!/usr/bin/env python
# encoding: utf-8

import scrapy
import datetime
import urllib
from bs4 import BeautifulSoup as bs

from datetime import datetime as dte
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter, vcode_zhw
from base import SpiderBase
from scrapy.conf import settings
from pymongo import MongoClient
import requests

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
        },
        # "DOWNLOAD_DELAY": 0.25,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    url = 'http://www.zhwsbs.gov.cn:9013/shfw/zaotsTicket/pageLists.xhtml'

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
        for x in xrange(3):
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
        days = 8
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
        sta_info = {
            u'香洲长途站': 'C1K001-102017',
            u'上冲站': 'C1K027-102018',
            u'南溪站': 'C1K013-102019',
            u'拱北通大站': 'C1K030-102023',
            u'斗门站': 'C2K003-102027',
            # u'井岸站': 'C2K001-102028',
            u'红旗站': 'C1K006-102030',
            u'三灶站': 'C1K004-102031',
            u'平沙站': 'C1K007-102032',
            u'南水站': 'C1K008-102033',
            u'唐家站': 'TJZ001-102020',
            u'金鼎站': 'JDZ001-102021',
            u'拱北票务中心': 'GBPW01-102024',
            u'西埔站': 'XPZ001-102029',
        }
        code, cookies = self.update_cookies()
        for s_name, s_id in sta_info.items():
            start = {"name": s_name, "id": s_id, "code": get_pinyin_first_litter(s_name)}
            for y in xrange(self.start_day(), days):
                for es in self.get_dest_list("广东", "珠海", s_name):
                    name, d_code = es["name"], es["code"]
                    end = {"name": name, "code": d_code}
                    sdate = str(today + datetime.timedelta(days=y))
                    if self.has_done(start["name"], end["name"], sdate):
                        continue
                    data['SchDstNodeName'] = end["name"]
                    data['SchDate'] = sdate
                    data['checkCode'] = code
                    data['StartStation'] = s_id
                    yield scrapy.Request(
                        url=self.url,
                        callback=self.parse_line,
                        method='POST',
                        body=urllib.urlencode(data),
                        headers=headers,
                        cookies=dict(cookies),
                        meta={
                            'start': start,
                            'end': end,
                            'sdate': sdate,
                        },
                    )

    def parse_line(self, response):
        end = response.meta['end']
        start = response.meta['start']
        sdate = response.meta['sdate'].decode('utf-8')
        self.mark_done(start["name"], end["name"], sdate)

        soup = bs(response.body, 'lxml')
        info = soup.find('table', attrs={'id': 'changecolor'})
        items = info.find_all('tr', attrs={'id': True})
        self.logger.info("%s=>%s %s, result: %s", start["name"], end["name"], sdate, len(items))
        for i, x in enumerate(items):
            i = i + 1
            try:
                y = x.find_all('td')
                sts = x.find('input', attrs={'class': 'g_table_btn'}).get('value')
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
                    s_city_name="珠海",
                    s_sta_name=s_sta_name,
                    s_city_code="zh",
                    s_sta_id=start["id"],
                    d_city_name=end["name"],
                    d_city_id="",
                    d_city_code=end["code"],
                    d_sta_id="",
                    d_sta_name=d_sta_name,
                    drv_date=drv_date,
                    drv_time=drv_time,
                    drv_datetime=dte.strptime("%s %s" % (
                        drv_date, drv_time), "%Y-%m-%d %H:%M"),
                    distance='',
                    vehicle_type=vehicle_type,
                    seat_type="",
                    bus_num=extra['txtSchLocalCode'],
                    full_price=float(extra['txtSchPrice']),
                    half_price=float(extra['txtSchPrice']) / 2,
                    fee=0.0,
                    crawl_datetime=dte.now(),
                    extra_info=extra,
                    left_tickets=int(left_tickets),
                    crawl_source="zhw",
                    shift_id="",
                )
                if sts in [u'不在服务时间', u'立即购买']:
                    yield LineItem(**attrs)

            except Exception, e:
                self.logger.error(e)

#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests
import urllib
import re
import urlparse
from lxml import etree

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis


class BjkySpider(SpiderBase):
    name = "bjky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
#             'BusCrawl.middleware.ProxyMiddleware': 410,
#             'BusCrawl.middleware.BjkyHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
#         "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        start_url = "http://www.e2go.com.cn/TicketOrder/SearchSchedule"
#         cookie ="Hm_lvt_0b26ef32b58e6ad386a355fa169e6f06=1456970104,1457072900,1457316719,1457403102; ASP.NET_SessionId=uuppwd3q4j3qo5vwcka2v04y; Hm_lpvt_0b26ef32b58e6ad386a355fa169e6f06=1457415243"
#         headers={"cookie":cookie} 
        cookies = {"Hm_lvt_0b26ef32b58e6ad386a355fa169e6f06": "1456970104,1457072900,1457316719,1457403102",
                                       "ASP.NET_SessionId": "uuppwd3q4j3qo5vwcka2v04y",
                                       "Hm_lpvt_0b26ef32b58e6ad386a355fa169e6f06": "1457415243"}
        yield scrapy.Request(start_url,
                             method="GET",
                             cookies=cookies,
                             callback=self.parse_url,
                             meta={'cookies': cookies})

    def parse_url(self, response):
        cookies = response.meta["cookies"]
        result = urlparse.urlparse(response.url)
        if result.path == '/Home/Login':
            self.logger.error("parse_url: cookie is expire", )
            return
        letter = 'abcdefghijklmnopqrstuvwxyz'
        for i in letter:
            for j in letter:
                query = i+j
                end_station_url = 'http://www.e2go.com.cn/Home/GetBusStops?q=%s'%query
                yield scrapy.Request(end_station_url,
                                     method="GET",
                                     callback=self.parse_end_city,
                                     meta={'cookies': cookies})

    def parse_end_city(self, response):
        cookies = response.meta["cookies"]
        res = json.loads(response.body)
        queryline_url = "http://www.e2go.com.cn/TicketOrder/SearchSchedule"
        for end in res:
            today = datetime.date.today()
            for i in range(0, 5):
                sdate = str(today+datetime.timedelta(days=i))
                data = {
                    "ArrivingStop": unicode(end['City']),
                    "ArrivingStopId": unicode(end['StopId']),
                    "ArrivingStopJson": json.dumps(end),
                    "DepartureDate": sdate,
                    "Order": "DepartureTimeASC",
                    "RideStation": '全部',
                    "RideStationId": "-1"
                }
                yield scrapy.FormRequest(queryline_url, formdata=data,
                                         callback=self.parse_line,
                                         cookies=cookies,
                                         meta={"data":data,"end": end, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        data = response.meta["data"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        content = response.body
        print '33333333333333333333',type(content)
        if isinstance(content, unicode):
            pass
        else:
            content = content.decode('utf-8')
        sel = etree.HTML(content)
        scheduleList = sel.xpath('//div[@id="scheduleList"]/table/tbody/tr')
        print '333333333',len(scheduleList)
        for i in range(0,len(scheduleList),2):
            s = scheduleList[i]
            time = s.xpath('td[@class="departureTimeCell"]/span/text()')[0]
            station = s.xpath('td[@class="routeNameCell"]/span/text()')
            scheduleIdSpan = s.xpath('td[@class="scheduleAndBusLicenseCes"]/span[@class="scheduleSpan"]/span[@class="scheduleIdSpan"]/text()')[0]
            scheduleIdSpan = scheduleIdSpan.replace('\r\n', '').replace('\t',  '').replace(' ',  '')
            price = s.xpath('td[@class="ticketPriceCell"]/span[@class="ticketPriceSpan"]/span[@class="ticketPriceValueSpan"]/text()')[0]
            ScheduleString = s.xpath('td[@class="operationCell"]/@data-schedule')[0]


            station_code_mapping = {
                u"六里桥": "1000",
                u"首都机场站": "1112",
                u"赵公口": "1103",
                u"木樨园": "1104",
                u"丽泽桥": "1106",
                u"新发地": "1107",
                u"莲花池": "1108",
                u"四惠": "1109",
                u"永定门": "1110",
                u"北郊": "1111",
                }
            print station_code_mapping[station[0]]
            attrs = dict(
                s_province = '北京',
                s_city_name = "北京",
                s_city_id = '',
                s_city_code= get_pinyin_first_litter(u"北京"),
                s_sta_name = station[0],
                s_sta_id = station_code_mapping[station[0]],
                d_city_name = station[1],
                d_city_code= get_pinyin_first_litter(station[1]),
                d_city_id = '',
                d_sta_name = station[1].decode('utf-8'),
                d_sta_id = '',
                drv_date = sdate,
                drv_time = time,
                drv_datetime = dte.strptime("%s %s" % (sdate, time), "%Y-%m-%d %H:%M"),
                distance = "0",
                vehicle_type = "",
                seat_type = "",
                bus_num = scheduleIdSpan,
                full_price = float(price),
                half_price = float(price)/2,
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"ScheduleString":ScheduleString,"ArrivingStopJson":data['ArrivingStopJson']},
                left_tickets = 50,
                crawl_source = "bjky",
                shift_id="",
            )
            yield LineItem(**attrs)



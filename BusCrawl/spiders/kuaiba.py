#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests
import urllib
import re

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis


class KuaibaSpider(SpiderBase):
    name = "kuaiba"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.KuaibaHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
#         "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    base_url = 'http://m.daba.cn'

    def start_requests(self):
        start_url = "http://m.daba.cn/jsp/line/newlines.jsp"
        yield scrapy.Request(start_url,
                             method="GET",
                             callback=self.parse_url)

    def parse_url(self, response):
        res = response.body
        list_url = re.findall(r'query_line_list : (.*),', res)[0][1:-1]
        line_url = re.findall(r'query_station : (.*),', res)[0][1:-1]
        start_url = re.findall(r'allCity: (.*),', res)[0][1:-1]
        list_url = self.base_url+list_url
        line_url = self.base_url+line_url
        yield scrapy.Request(start_url,
                             method="GET",
                             callback=self.parse_start_city,
                             meta={"list_url": list_url, "line_url": line_url})

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["code"] != "100":
            self.logger.error("parse_start_city: Unexpected return, %s", res)
            return
        list_url = response.meta["list_url"]
        line_url = response.meta["line_url"]
        start_list = []
        end_list = []
        cities = res['data']['cities']
        for city in cities:
            if city['county'] == u'北京' and city['county']== city['name'] and  (city['cityType'] == 1 or city['cityType'] == 3):
                start_list.append(city)
        for city in cities:
            if (city['cityType'] == 2 or city['cityType'] == 3):
                end_list.append(city)
#         print len(start_list)
#         print len(end_list)

#         start_list = [{u'letter': u'bj', u'name': u'北京',u'provinceName':'北京'}]
#         end_list =  [{u'letter': u'dx', u'name': u'定兴',u'provinceName':'河北'}]

        for start in start_list:
            for end in end_list:
                today = datetime.date.today()
                for i in range(0, 5):
                    sdate = str(today+datetime.timedelta(days=i))
                    params = {
                      "startDate": sdate,
                      "start": start["name"],
                      "arrive": end['name'],
                      "startStationList": '',
                      "endStationList": '',
                      }
                    line_list_url = "%s&%s" % (list_url, urllib.urlencode(params))
                    if self.has_done(start["name"], end["name"], sdate):
                        self.logger.info("ignore %s ==> %s %s" % (start["name"], end["name"], sdate))
                        continue
                    yield scrapy.Request(line_list_url,
                                         method="GET",
                                         callback=self.parse_line_list,
                                         meta={"start": start, "end": end, "date": sdate,'line_url':line_url})

    def parse_line_list(self, response):
        "解析班车列表"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        line_url = response.meta["line_url"]
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        self.mark_done(start["name"], end["name"], sdate)
        if res['code'] == 0 and res['data'] and len(res['data']['lineList']) > 0:
            tempCloseEnd = dte.strptime(res['data']['tempCloseEnd'], "%Y-%m-%d %H:%M:%S")
            tempCloseStart = dte.strptime(res['data']['tempCloseStart'], "%Y-%m-%d %H:%M:%S")
            now = dte.now()

            if now > tempCloseStart and now < tempCloseEnd:#"网上停售"
                return
            else:
                if not res['data']['cityOpenSale']: #当前线路暂不支持网上售票，快巴正在努力开通中
                    return
                else:
                    startCity = res['data']['startCity']
                    arriveCity = res['data']['arriveCity']
                    lineList = res['data']['lineList']
                    for line in lineList:
                        if line['lineStatus'] == 3:
                            params = {
                                  "endTime": line['lastBus'],
                                  "startCity": startCity,
                                  "startStation": line['startStation'],
                                  "arriveCity": arriveCity,
                                  "arriveStation": line['arriveStation'],
                                  "startDate": sdate,
                                  "startTime": line['firstBus'],
                                  }
                            url = "%s&%s" % (line_url, urllib.urlencode(params))
                            yield scrapy.Request(url,
                                                 method="GET",
                                                 callback=self.parse_line,
                                                 meta={"start": start, "end": end,"params":params})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        params = response.meta["params"]
        sdate = params["startDate"]
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if end['name'] != params['arriveStation']:
            print params["startCity"], params["arriveStation"], sdate
            self.mark_done(params["startCity"], params["arriveStation"], sdate)
        busTripInfoSet = res['data']['busTripInfoSet']
        cityOpenSale = res['data']['cityOpenSale']
        if len(busTripInfoSet) > 0 and cityOpenSale:
            for d in busTripInfoSet:
                if d['tickets'] == 0 or d['tempClose'] == 1:
                    continue
                attrs = dict(
                    s_province = start['provinceName'],
                    s_city_name = params['startCity'],
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(params['startCity']),
                    s_sta_name = params['startStation'],
                    s_sta_id = '',
                    d_city_name = params['arriveCity'],
                    d_city_code= get_pinyin_first_litter(params['arriveCity']),
                    d_city_id = '',
                    d_sta_name = params['arriveStation'],
                    d_sta_id = '',
                    drv_date = sdate,
                    drv_time = d["time"],
                    drv_datetime = dte.strptime("%s %s" % (sdate, d["time"][0:-3]), "%Y-%m-%d %H:%M"),
                    distance = "0",
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = d["id"],
                    full_price = float(d["price"]),
                    half_price = float(d["price"])/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {"startTime":params['startTime'],"endTime":params['endTime']},
                    left_tickets = int(d["tickets"]),
                    crawl_source = "kuaiba",
                    shift_id="",
                )
                print attrs
                yield LineItem(**attrs)



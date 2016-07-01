# -*- coding: utf-8 -*-
import scrapy
import json
import datetime
import pypinyin
import re
from lxml import etree
from datetime import datetime as dte

from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase


class LnkySpider(SpiderBase):
    name = "lnky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware':None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
#             'BusCrawl.middlewares.common.ProxyMiddleware': 410,
            'BusCrawl.middleware.LnkyHeaderMiddleware': 410,
        }
    }

    def start_requests(self):
        url = "http://www.84100.com/"
        return [scrapy.Request(url, callback=self.parse_start_city)]

    def parse_start_city(self, response):
        res = response.body
        matchObj = re.findall('var startCityJson = (.*);', res)
        #print b[0][1:-1]
        provinceInfo = json.loads(matchObj[0][1:-1])
        province_id = '210000'
        for province in provinceInfo[province_id]:
            if not self.is_need_crawl(city=province["cityName"]):
                continue
            for start in province['countyList']:
                target_url = 'http://www.84100.com/getEndPortList/ajax?cityId=%s'%int(str(start['countyId']))
                yield scrapy.Request(target_url, callback=self.parse_target_city,
                                     meta={"start": start})

    def parse_target_city(self, response):
        "解析目的地城市"
        targetCity = json.loads(response.body)
        start = response.meta["start"]
        ports = targetCity.get('ports', [])
#         ports = [{'portName':'夏郢','pinyinPrefix':'rx'}]
        if ports:
            for end in ports:
                today = datetime.date.today()
                for i in range(0, 10):
                    sdate = str(today+datetime.timedelta(days=i))
                    if self.has_done(self.name+start["countyName"], end['portName'], sdate):
                        #self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                        continue
                    queryline_url = 'http://www.jt306.cn/wap/ticketSales/ticketList.do'
                    payload = {
                        "endCityName": end['portName'],
                        "startCityName": start['countyName'],
                        "startDate": sdate
                            }
                    yield scrapy.FormRequest(queryline_url, formdata=payload, callback=self.parse_line,
                                             meta={"sdate": sdate,'start':start, "end":end})

    def parse_line(self, response):
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["sdate"]
        content = response.body
        if not isinstance(content, unicode):
            content = content.decode('utf-8')
        self.mark_done(self.name+start["countyName"], end['portName'], sdate)
        sel = etree.HTML(content)
        scheduleInfo = sel.xpath('//input[@id="scheduleInfoJson"]/@value')
        if scheduleInfo:
            scheduleInfo = json.loads(scheduleInfo[0])
            for d in scheduleInfo:
                if not isinstance(d, dict):
                    continue
                if int(d['seatLast']) == 0:
                    continue
                if float(d["price"]) < 5:
                    continue
                attrs = dict(
                    s_province = '辽宁',
                    s_city_name = start['countyName'],
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(start['countyName']),
                    s_sta_name = d['fromStation'],
                    s_sta_id = '',
                    d_city_name = end['portName'],
                    d_city_code= get_pinyin_first_litter(end['portName']),
                    d_city_id = '',
                    d_sta_name = d['toStation'],
                    d_sta_id = '',
                    drv_date = sdate,
                    drv_time = d["driveTime"],
                    drv_datetime = dte.strptime("%s %s" % (sdate, d["driveTime"]), "%Y-%m-%d %H:%M"),
                    distance = "0",
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = d['trainNumber'],
                    full_price = float(d["price"]),
                    half_price = float(d["price"])/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {'lineNo':d['lineNo']},
                    left_tickets = int(d["seatLast"]),
                    crawl_source = "lnky",
                    shift_id= '',
                )
                yield LineItem(**attrs)


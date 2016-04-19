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
        url = "http://www.jt306.cn/wap/ticketSales/showCity.do"
        start_city_list = [u"沈阳市",u"大连市",
                           u"鞍山市",u"抚顺市",
                           u"本溪市",u"丹东市",
                           u"锦州市",u"营口市",
                           u"阜新市",u"辽阳市",
                           u"盘锦市",u"铁岭市",
                           u"朝阳市",u"葫芦岛市"
                           ]
        for start_name in start_city_list:
            if not self.is_need_crawl(city=start_name):
                continue
            data = {"departure": start_name}
            yield scrapy.FormRequest(url, formdata=data, callback=self.parse_target_city,
                                     meta={"start": start_name})

    def parse_target_city(self, response):
        "解析目的地城市"
        target_city_list = json.loads(response.body)
        start = response.meta["start"]
#         ports = [{'portName':'夏郢','pinyinPrefix':'rx'}]
        if target_city_list:
            for end in target_city_list:
                today = datetime.date.today()
                for i in range(0, 10):
                    sdate = str(today+datetime.timedelta(days=i))
                    if self.has_done(start, end[0], sdate):
                        #self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                        continue
                    queryline_url = 'http://www.jt306.cn/wap/ticketSales/ticketList.do'
                    payload = {
                        "endCityName": end[0],
                        "startCityName": start,
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
        self.mark_done(start, end[0], sdate)
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
                    s_city_name = start,
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(start),
                    s_sta_name = d['fromStation'],
                    s_sta_id = '',
                    d_city_name = end[0],
                    d_city_code= get_pinyin_first_litter(end[0]),
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


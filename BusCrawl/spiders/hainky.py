#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import re
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter


class HainkySpider(SpiderBase):
    name = "hainky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.HainkyHeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.2,
#         "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        url = 'http://www.0898hq.com:8088/HaiQiServer/purposeAction!getPurposes.action'
        station_dict ={
            "50":("海口汽车南站","海口"),
            "3":("海口汽车东站","海口"),
            "4":("海口西站(省际总站)","海口"),
            "1":("港口客运站(秀英港)","海口"),
            "5":("儋州(那大)车站","儋州"),
            "6":("三亚车站","三亚"),
            "23":("三亚西站","三亚"),
            "7":("文昌车站",'文昌'),
            "8":("五指山车站",'五指山'),
            "9":("东方(八所)车站",'东方'),
            "10":("定安车站",'定安'),
            "11":("万宁车站",'万宁'),
            "12":("琼海(加积)车站",'琼海'),
            "13":("陵水车站",'陵水'),
            "14":("屯昌车站",'屯昌'),
            "15":("临高车站",'临高'),
            "16":("昌江车站",'昌江'),
            "17":("白沙车站",'白沙'),
            "18":("乐东车站",'乐东'),
            "19":("保亭车站",'保亭'),
            "20":("澄迈车站",'澄迈'),
            "21":("琼中车站",'琼中'),
            "22":("黄流车站",'乐东')
            }
        for czbh, (station_name, city_name) in station_dict.items():
            data = {"czbh": czbh}
            start = {"czbh": czbh, 
                     "station_name": station_name,
                     "city_name": city_name}
            yield scrapy.FormRequest(url,
                                     method="POST",
                                     formdata=data,
                                     callback=self.parse_target_city,
                                     meta={"start": start})

    def parse_target_city(self, response):
        "解析目的地城市"
        res = json.loads(response.body)
        start = response.meta["start"]
        url = "http://www.0898hq.com:8088/HaiQiServer//queryScheduledAction!queryScheduled.action"
        for d in res:
            today = datetime.date.today()
            for i in range(0, 3):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start['station_name'], d["zdmc"], sdate):
                    self.logger.info("ignore %s ==> %s %s" % (start['station_name'], d["zdmc"], sdate))
                    continue
                fd = {
                    "ddzm": d["zdmc"],
                    "fcrq": sdate,
                    "fcsj_e": "24:00",
                    "fcsj_b": "00:00",
                    "czbh": start['czbh']
                }
                yield scrapy.FormRequest(url,
                                         formdata=fd,
                                         callback=self.parse_line,
                                         meta={"start": start, "end": d, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["sdate"]
        res = json.loads(response.body)
        self.logger.info("finish %s ==> %s" % (start["station_name"], end["zdmc"]))
        self.mark_done(start['station_name'], end["zdmc"], sdate)
        xml_text = re.findall(r"<getScheduledBusResult>(.*)</getScheduledBusResult>",res.get('msg', ''),re.S)[0]
        root = ET.fromstring(xml_text)
        node_find = root.find('Body')
        if node_find.attrib['size'] == '0':
            return
        res = node_find.findall('ScheduledBus')
        for d in res:
            s_sta_name = start['station_name']
            s_sta_id = start['czbh']
            d_city_name = end['zdmc']
            d_sta_name = d.find('MDZMC').text
            drv_time = d.find('FCSJ').text
            distance = d.find('LC').text
            seat_type = d.find('CXMC').text
            bus_num = d.find('CCBH').text
            full_price = d.find('PJ').text
            left_tickets = d.find('YPZS').text
            attrs = dict(
                s_province = '海南',
                s_city_name = start['city_name'],
                s_city_id = '',
                s_city_code= get_pinyin_first_litter(unicode(start['city_name'])),
                s_sta_name= s_sta_name,
                s_sta_id = s_sta_id,
                d_city_name = d_city_name,
                d_city_code= get_pinyin_first_litter(d_city_name),
                d_city_id = '',
                d_sta_name = d_sta_name,
                d_sta_id = '',
                drv_date = sdate,
                drv_time = drv_time,
                drv_datetime = dte.strptime("%s %s" % (sdate, drv_time), "%Y-%m-%d %H:%M"),
                distance = distance,
                vehicle_type = "",
                seat_type = seat_type,
                bus_num = bus_num,
                full_price = float(full_price),
                half_price = float(full_price)/2,
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {'end':end},
                left_tickets = int(left_tickets),
                crawl_source = "hainky",
                shift_id='',
            )
            yield LineItem(**attrs)



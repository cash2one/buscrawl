# -*- coding: utf-8 -*-
import scrapy
import json
import datetime
from datetime import datetime as dte
import pypinyin
import re
from lxml import etree

from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase


class XinTuYunSpider(SpiderBase):
    name = "xintuyun"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware':None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
#             'BusCrawl.middlewares.common.ProxyMiddleware': 410,
#             'BusCrawl.middlewares.scqcp.HeaderMiddleware': 410,
        }
    }

    def start_requests(self):
        url = "http://www.xintuyun.cn/"
        return [scrapy.Request(url, callback=self.parse_start_city)]

    def parse_start_city(self, response):
        res = response.body
#         print res
        matchObj = re.findall('var startCityJson = (.*);', res)
        #print b[0][1:-1]
        #print type(b[0])
        provinceInfo = json.loads(matchObj[0][1:-1])
        print provinceInfo['210000']

        crawl_province = {"province_id": '210000', 'province_name': u"辽宁"}
        province_id = crawl_province['province_id']
        for city in provinceInfo[province_id]:
            if not self.is_need_crawl(city=city["cityName"]):
                continue
            crawl_city = {"city_id": city['cityId'], 'city_name': city['cityName']}
            for j in city['countyList']:
                target_url = 'http://www.xintuyun.cn/getEndPortList/ajax?cityId=%s'%int(str(j['countyId']))
                yield scrapy.Request(target_url, callback=self.parse_target_city,
                                     meta={"crawl_province": crawl_province,'crawl_city':crawl_city,"start": j})

    def parse_target_city(self, response):
        "解析目的地城市"
        targetCity = json.loads(response.body)
        start = response.meta["start"]
        crawl_province = response.meta["crawl_province"]
        crawl_city = response.meta["crawl_city"]
        ports = targetCity.get('ports', [])
#         ports = [{'portName':'夏郢','pinyinPrefix':'rx'}]
        if ports:
            for port in ports:
                today = datetime.date.today()
                for i in range(0, 10):
                    sdate = str(today+datetime.timedelta(days=i))
                    if self.has_done(start["countyName"], port['portName'], sdate):
                        #self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                        continue
                    queryline_url = 'http://www.xintuyun.cn/getTrainList/ajax'
                    payload = {
                        'companyNames': '',
                        'endName': port['portName'],
                        "isExpressway": '',
                        "sendDate": sdate,
                        "sendTimes": '',
                        "showRemainOnly": '',
                        "sort": "1",
                        "startId": start['countyId'],
                        'startName': start['countyName'],
                        'stationIds': '',
                        'ttsId': ''
                        }
                    yield scrapy.FormRequest(queryline_url, formdata=payload, callback=self.parse_line,
                                             meta={"payload": payload, 'crawl_province':crawl_province,'crawl_city':crawl_city,'start':start, "end":port})

    def parse_line(self, response):
        trainListInfo = json.loads(response.body)
        if trainListInfo:
            start = response.meta["start"]
            end = response.meta["end"]
            crawl_province = response.meta["crawl_province"]
            crawl_city = response.meta["crawl_city"]
            payload = response.meta["payload"]
            sdate = payload['sendDate']
            nextPage = int(trainListInfo['nextPage'])
            pageNo = int(trainListInfo['pageNo'])
    #                             print m['msg']
            content = trainListInfo['msg']
            if not isinstance(content, unicode):
                content = content.decode('utf-8')
            sel = etree.HTML(content)
            trains = sel.xpath('//div[@class="trainList"]')
            for n in trains:
                flag = 0
                buyInfo = n.xpath('ul/li[@class="buy"]/a[@class="btn"]/text()')
                if buyInfo:
                    d_str = n.xpath("@data-list")[0]
                    shift_str = d_str[d_str.index("id=")+3:]
                    left_str = d_str[d_str.index("leftSeatNum=")+12:]
                    shiftid = shift_str[:shift_str.index(",")]
                    leftSeatNum = left_str[:left_str.index(",")]
                    station = n.xpath('ul/li[@class="start"]/p/text()')
                    time = n.xpath('ul/li[@class="time"]/p/strong/text()')
                    bus_num = ''
                    bus_num = n.xpath('ul/li[@class="time"]/p[@class="carNum"]/text()')
                    if bus_num:
                        bus_num = bus_num[0].replace('\r\n', '').replace(' ',  '')
                    price = n.xpath('ul/li[@class="price"]/strong/text()')
                    flag = 1
                    attrs = dict(
                        s_province = crawl_province['province_name'],
                        s_city_name = start['countyName'],
                        s_city_id = start['countyId'],
                        s_city_code= get_pinyin_first_litter(start['countyName']),
                        s_sta_name= station[0],
                        s_sta_id = start['countyId'],
                        d_city_name = end['portName'],
                        d_city_code= get_pinyin_first_litter(end['portName']),
                        d_city_id = '',
                        d_sta_name = station[1],
                        d_sta_id = '',
                        drv_date = sdate,
                        drv_time = time[0],
                        drv_datetime = dte.strptime("%s %s" % (sdate, time[0]), "%Y-%m-%d %H:%M"),
                        distance = 0,
                        vehicle_type = "",
                        seat_type = '',
                        bus_num = bus_num.decode("utf-8").strip().rstrip(u"次"),
                        full_price = float(str(price[0]).split('￥')[-1]),
                        half_price = float(str(price[0]).split('￥')[-1])/2,
                        fee = 0,
                        crawl_datetime = dte.now(),
                        extra_info = {"flag": flag},
                        left_tickets = int(leftSeatNum),
                        crawl_source = "xintuyun",
                        shift_id=shiftid,
                    )
                    yield LineItem(**attrs)

            if nextPage > pageNo:
                url = 'http://www.xintuyun.cn/getBusShift/ajax'+'?pageNo=%s' % nextPage
                yield scrapy.FormRequest(url, formdata=payload, callback=self.parse_line,
                                         meta={"payload": payload, 'crawl_province':crawl_province,'crawl_city':crawl_city,'start':start, "end":end})
            elif nextPage and nextPage == pageNo:
                self.mark_done(start["countyName"], end['portName'], sdate)

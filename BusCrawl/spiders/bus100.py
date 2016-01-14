# -*- coding: utf-8 -*-
import scrapy
import json
import datetime
import urllib
import sys
from BusCrawl.utils.tool import md5


import re
import requests

from lxml import etree


from BusCrawl.items.bus100 import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter


class bus100Spider(scrapy.Spider):
    name = "bus100"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipelines.bus100.MongoBus100Pipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware':None,
            'BusCrawl.middlewares.common.BrowserRandomUserAgentMiddleware': 400,
#             'BusCrawl.middlewares.common.ProxyMiddleware': 410,
#             'BusCrawl.middlewares.scqcp.HeaderMiddleware': 410,
        }
    }

    def __init__(self, province_id=None, *args, **kwargs):
        if province_id:
            self.province_id = province_id
        else:
            self.province_id = None
        super(bus100Spider, self).__init__(*args, **kwargs)

    def start_requests(self):
        url = "http://www.84100.com/"
        return [scrapy.Request(url, callback=self.parse_start_city)]

    def parse_start_city(self, response):
        res = response.body
#         print res
        matchObj = re.findall('var startCityJson = (.*);', res)
        #print b[0][1:-1]
        #print type(b[0])
        provinceInfo = json.loads(matchObj[0][1:-1])
#         print provinceInfo
#         print provinceInfo['450000']
        #crawl_province_list = [{"province_id":'450000','province_name':"广西"},{"province_id":'370000','province_name':"山东"},{"province_id":'210000','province_name':"辽宁"}]

        crawl_province = {"province_id": '450000', 'province_name': "广西"}
        province_id = crawl_province['province_id']
        if self.province_id:
            province_id = self.province_id
            crawl_province_dict = {
                              '450000': {"province_id": '450000', 'province_name': "广西"},
                              '370000': {"province_id": '370000', 'province_name': "山东"},
                              '210000': {"province_id": '210000', 'province_name': "辽宁"}
                              }
            crawl_province = crawl_province_dict.get(province_id)
        for province in provinceInfo[province_id]:
            cityId = province['cityId']
            city_name = province['cityName']
            crawl_city = {"city_id": cityId, 'city_name': city_name}
            for j in province['countyList']:
                target_url = 'http://www.84100.com/getEndPortList/ajax?cityId=%s'%int(str(j['countyId']))
                yield scrapy.Request(target_url, callback=self.parse_target_city, 
                                     meta={"crawl_province": crawl_province,'crawl_city':crawl_city,"start": j})

    def parse_target_city(self, response):
        "解析目的地城市"
        targetCity = json.loads(response.body)
        start = response.meta["start"]
        crawl_province = response.meta["crawl_province"]
        crawl_city = response.meta["crawl_city"]
        ports = targetCity.get('ports', [])
        if ports:
            for port in ports:
                today = datetime.date.today()
                for i in range(0, 10):
                    sdate = str(today+datetime.timedelta(days=i))
                    queryline_url = 'http://www.84100.com/getTrainList/ajax'
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
#         trainListInfo= trainListInfo.json()

        if trainListInfo:
            start = response.meta["start"]
            end = response.meta["end"]
            crawl_province = response.meta["crawl_province"]
            crawl_city = response.meta["crawl_city"]
            payload = response.meta["payload"]
            item = LineItem()
            item['province_id'] = crawl_province['province_id']
            item['province_name'] = crawl_province['province_name']

            item['city_id'] = crawl_city["city_id"]
            item['city_name'] = crawl_city["city_name"]
            item['city_short_name'] = get_pinyin_first_litter(item['city_name'])

            item['start_city_name'] = start['countyName']
            item['start_city_id'] = start['countyId']
            item['start_full_name'] = start['pinyin']
            start_short_name = start['pinyinPrefix']
            if not start_short_name or start_short_name == 'null':
                start_short_name = get_pinyin_first_litter(item['start_city_name'])
            item['start_short_name'] = start_short_name

            item['target_city_name'] = end['portName']
            item['target_short_name'] = end['pinyinPrefix']
            item['target_full_name'] = end['pinyin']

            sdate = payload['sendDate']

            nextPage = int(trainListInfo['nextPage'])
            pageNo = int(trainListInfo['pageNo'])
    #                             print m['msg']
            sel = etree.HTML(trainListInfo['msg'])
            trains = sel.xpath('//div[@class="trainList"]')
            for n in trains:
                station = n.xpath('ul/li[@class="start"]/p/text()')
                item['start_station'] =station[0]
                item['end_station'] =station[1]
    
                time = n.xpath('ul/li[@class="time"]/p/strong/text()')
                item['departure_time'] = sdate+' '+time[0]
    #             print 'time->',time[0]
                banci = n.xpath('ul/li[@class="time"]/p[@class="banci"]/text()')
    #             print 'banci->',banci[0]
                item['banci'] = banci[0]
                price = n.xpath('ul/li[@class="price"]/strong/text()')
    #             print 'price->',price[0]
                item['price'] = price[0]
                infor = n.xpath('ul/li[@class="infor"]/p/text()')
                distance = infor[1].replace('\r\n', '').replace(' ',  '')
    #             print 'distance->',distance
                item['distance'] = distance
                buyInfo = n.xpath('ul/li[@class="buy"]')
                flag = 0
                shiftid = 0
                for buy in buyInfo:
                    flag = buy.xpath('a[@class="btn"]/text()')   #判断可以买票
                    if flag:
                        flag = 1
                        shiftInfo = buy.xpath('a[@class="btn"]/@onclick')
                        if shiftInfo:
                            shift = re.findall("('(.*)')", shiftInfo[0])
                            if shift:
                                shiftid = shift[0][1]
                    else:
                        flag = 0
                item['flag'] = flag
                item['shiftid'] = shiftid
                item['crawl_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                line_id = md5("%s-%s-%s-%s-%s-%s" % \
                    (item["start_city_name"], item["start_city_id"], item["target_city_name"], item["departure_time"],item['banci'], 'bus100'))
                item['line_id'] = line_id
                item['crawl_source'] = 'bus100'
                yield item
            if nextPage > pageNo:
                url = response.url.split('?')[0]+'?pageNo=%s'%nextPage
                yield scrapy.FormRequest(url, formdata=payload, callback=self.parse_line, 
                                         meta={"payload": payload, 'crawl_province':crawl_province,'crawl_city':crawl_city,'start':start, "end":end})
            
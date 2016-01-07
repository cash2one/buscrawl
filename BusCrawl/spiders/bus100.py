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
        crawl_province_list = [{"province_id":'450000','province_name':"广西"},{"province_id":'370000','province_name':"山东"},{"province_id":'210000','province_name':"辽宁"}]

        for crawl_province in crawl_province_list:
            province_id = crawl_province['province_id']
            province_name = crawl_province['province_name']
            for province in provinceInfo[province_id]:
                cityId = province['cityId']
                city_name = province['cityName']

                for j in province['countyList']:
                    target_url = 'http://www.84100.com/getEndPortList/ajax?cityId=%s'%int(str(j['countyId']))
                    targetCityInfo = requests.get(target_url)
    #                 print targetCityInfo
                    targetCity = targetCityInfo.json()
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
                                    "startId": j['countyId'],
                                    'startName': j['countyName'],
                                    'stationIds': '',
                                    'ttsId': ''
                                    }
    
                                yield scrapy.FormRequest(queryline_url, formdata=payload, callback=self.parse_line, 
                                                         meta={"payload": payload, 'province_id':province_id,'province_name':province_name, "data":j,"city_name":city_name,"city_id":cityId,'port':port})

    def parse_line(self, response):
        trainListInfo = json.loads(response.body)
#         trainListInfo= trainListInfo.json()

        if trainListInfo:
            data = response.meta["data"]
            port = response.meta["port"]
            payload = response.meta["payload"]
            item = LineItem()
            item['province_id'] = response.meta["province_id"]
            item['province_name'] = response.meta["province_name"]

            item['city_id'] = response.meta["city_id"]
            item['city_name'] = response.meta["city_name"]
            item['city_short_name'] = get_pinyin_first_litter(item['city_name'])

            item['start_city_name'] = data['countyName']
            item['start_city_id'] = data['countyId']
            item['start_full_name'] = data['pinyin']
            start_short_name = data['pinyinPrefix']
            if not start_short_name or start_short_name == 'null':
                start_short_name = get_pinyin_first_litter(item['start_city_name'])
            item['start_short_name'] = start_short_name

            item['target_city_name'] = port['portName']
            item['target_short_name'] = port['pinyinPrefix']
            item['target_full_name'] = port['pinyin']

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
                yield scrapy.FormRequest(url, formdata=payload, callback=self.parse_line, meta={"payload": payload,
                    'province_id':response.meta["province_id"],'province_name':response.meta["province_name"], "data":data,"city_id":response.meta["city_id"], "city_name":response.meta["city_name"],'port':port})
            
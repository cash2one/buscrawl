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


from BusCrawl.items.gx84100 import LineItem, StartCityItem, TargetCityItem
from BusCrawl.utils.tool import get_pinyin_first_litter


class gx84100Spider(scrapy.Spider):
    name = "gx84100"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipelines.gx84100.MongoGx84100Pipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware':None,
            'BusCrawl.middlewares.common.BrowserRandomUserAgentMiddleware': 400 ,
#             'BusCrawl.middlewares.common.ProxyMiddleware': 410,
#             'BusCrawl.middlewares.scqcp.HeaderMiddleware': 410,
        }
    }

    def start_requests(self):
        url = "http://www.84100.com/"
        return [scrapy.Request(url, callback=self.parse_start_city)]

    def parse_start_city(self, response):
        res = response.body
        print res
        matchObj = re.findall('var startCityJson = (.*);', res)
        #print b[0][1:-1]
        #print type(b[0])
        provinceInfo = json.loads(matchObj[0][1:-1])
#         print provinceInfo
#         print provinceInfo['450000']

        province_id = '450000'
        for province in provinceInfo[province_id]:
            cityId = province['cityId']
            city_name = province['cityName']
            city_short_name = get_pinyin_first_litter(city_name)
#             item = LineItem()
#             item['province_id']='450000'
#             item['city_id'] = cityId
#             item['city_name'] = city_name
            for j in province['countyList']:
                startCityItem = StartCityItem()
                start_city_name = j['countyName']
                start_city_id = j['countyId']
                start_full_name = j['pinyin']
                start_short_name = j['pinyinPrefix']
                if not start_short_name or start_short_name == 'null':
                    start_short_name = get_pinyin_first_litter(start_city_name)
#                 item['start_city_name'] = start_city_name
#                 item['start_city_id'] = start_city_id
                startCityItem['province_id'] = province_id
                startCityItem['city_id'] = cityId
                startCityItem['city_name'] = city_name
                startCityItem['city_short_name'] = city_short_name
                startCityItem['start_city_name'] = start_city_name
                startCityItem['start_city_id'] = start_city_id
                startCityItem['start_full_name'] = start_full_name
                startCityItem['start_short_name'] = start_short_name
                yield startCityItem
                target_url = 'http://www.84100.com/getEndPortList/ajax?cityId=%s'%int(str(start_city_id))
                targetCityInfo = requests.get(target_url)
#                 print targetCityInfo
                targetCity = targetCityInfo.json()
                ports = targetCity.get('ports', [])

                if ports:
                    for port in ports:
                        targetCityItem = TargetCityItem()
                        target_city_name = port['portName']
                        targetCityItem['starting_id'] = start_city_id
                        targetCityItem['full_name'] = port['pinyin']
                        targetCityItem['short_name'] = port['pinyinPrefix']
                        targetCityItem['short_name'] = port['pinyinPrefix']
                        targetCityItem['target_name'] = target_city_name
                        yield targetCityItem
                        today = datetime.date.today()
                        for i in range(0, 2):
                            sdate = str(today+datetime.timedelta(days=i))
                            queryline_url = 'http://www.84100.com/getTrainList/ajax'
                            payload = {
                                'companyNames': '',
                                'endName': target_city_name,
                                "isExpressway": '',
                                "sendDate": sdate,
                                "sendTimes": '',
                                "showRemainOnly": '',
                                "sort": "1",
                                "startId": start_city_id,
                                'startName': start_city_name,
                                'stationIds': '',
                                'ttsId': ''
                                }

                            yield scrapy.FormRequest(queryline_url, formdata=payload, callback=self.parse_line, 
                                                     meta={"payload": payload, 'province_id':province_id, "city_id":cityId,"city_name":city_name})

    def parse_line(self, response):
        trainListInfo = json.loads(response.body)
#         trainListInfo= trainListInfo.json()

        if trainListInfo:
            item = LineItem()
            item['province_id'] = response.meta["province_id"]
            item['city_id'] = response.meta["city_id"]
            item['city_name'] = response.meta["city_name"]
            payload = response.meta["payload"]
            sdate = payload['sendDate']
            item['start_city_name'] = payload['startName']
            item['start_city_id'] = payload['startId']
            item['target_city_name'] = payload['endName']
            nextPage = int(trainListInfo['nextPage'])
            pageNo = int(trainListInfo['pageNo'])
    #                             print m['msg']
            sel = etree.HTML(trainListInfo['msg'])
            trains = sel.xpath('//div[@class="trainList"]')
            for n in trains:
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
                    (item["start_city_name"], item["start_city_id"], item["target_city_name"], item["departure_time"],item['banci'], 'gx84100'))
                item['line_id'] = line_id
                yield item
            if nextPage > pageNo:
                url = response.url.split('?')[0]+'?pageNo=%s'%nextPage
                yield scrapy.FormRequest(url, formdata=payload, callback=self.parse_line, meta={"payload": payload,
                    'province_id':response.meta["province_id"], "city_id":response.meta["city_id"], "city_name":response.meta["city_name"]})
            
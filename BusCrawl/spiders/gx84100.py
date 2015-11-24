# -*- coding: utf-8 -*-
import scrapy
import json
import datetime
import urllib
import sys


import re
import requests

from lxml import etree


from BusCrawl.items.gx84100 import LineItem

class gx84100Spider(scrapy.Spider):
    name = "gx84100"
    
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipelines.gx84100.MongoGx84100Pipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middlewares.common.BrowserRandomUserAgentMiddleware': 400,
#             'BusCrawl.middlewares.common.ProxyMiddleware': 410,
#             'BusCrawl.middlewares.scqcp.HeaderMiddleware': 410,
        }
    }

    def start_requests(self):
        
        url = "http://www.84100.com/"
        a=requests.get(url)
        res = a.content
        b= re.findall('var startCityJson = (.*);',res)
        #print b[0][1:-1]
        #print type(b[0])
        provinceInfo=json.loads(b[0][1:-1])
#         print provinceInfo
#         print provinceInfo['450000']
        count_city=0
        start_city_count=0
        port_count=0
        for province in provinceInfo['450000']:
            count_city=+1 
            cityId = province['cityId']
            city_name = province['cityName']
            
            
            item = LineItem()      
            item['province_id']='450000'
            item['city_id'] = cityId
            item['city_name'] = city_name
            
            
            for j in  province['countyList']:
                start_city_count=+1
                start_city_name = j['countyName']
                start_city_id  = j['countyId']
                
                item['start_city_name'] = start_city_name
                item['start_city_id'] = start_city_id
                
                
                target_url ='http://www.84100.com/getEndPortList/ajax?cityId=%s'%int(str(start_city_id))
                print target_url
                targetCityInfo=requests.get(target_url)
#                 print targetCityInfo
                targetCity= targetCityInfo.json()
                print targetCity
                ports = targetCity.get('ports',[])
        
                if ports:
                    for port in ports:
                        port_count=+1
                        target_city_name = port['portName']
                        
                        item['target_city_name'] = target_city_name
                        
                        today = datetime.date.today()
                        for i in range(0, 20):
                            sdate = str(today+datetime.timedelta(days=i))
                            queryline_url='http://www.84100.com/getTrainList/ajax'
                                      
                            payload={
                                'companyNames'    :'',
                                'endName'    :target_city_name,
                                "isExpressway"   :'', 
                                "sendDate"    :sdate,
                                "sendTimes"  :''  ,
                                "showRemainOnly"    :'',
                                "sort" :  "1",
                                "startId"  :start_city_id,
                                'startName' :start_city_name  ,
                                'stationIds':'',
                                'ttsId':''
                                }
                            

                            yield scrapy.FormRequest(queryline_url, formdata=payload, callback=self.parse_line, meta={"payload": payload,'item':item})
        
        
        print  count_city
        print  start_city_count
        print  port_count
        
                         
#                             trainListInfo = requests.post(queryline_url, data=payload)
#     def parse_line1(self, response):    
#         pass                    
    def parse_line(self, response):
        
        trainListInfo = json.loads(response.body)
                        
#         trainListInfo= trainListInfo.json()
        
        item_bak = response.meta["item"]
        item=item_bak
        payload = response.meta["payload"]
        sdate=payload['sendDate']
        if trainListInfo:
#             print trainListInfo
            nextPage  = trainListInfo['nextPage']
            pageNo = trainListInfo['pageNo']
            
    #                             print m['msg']
            sel = etree.HTML(trainListInfo['msg'])
            trains= sel.xpath('//div[@class="trainList"]')
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
                distance = infor[1].replace('\r\n','').replace(' ','')
    #             print 'distance->',distance
                item['distance'] = distance
                
                buy = n.xpath('ul/li[@class="buy"]')
                flag=0
                shiftid=0
                for b in buy:
                    flag= b.xpath('a[@class="btn"]/text()') #判断可以买票
                    if flag:
                        flag=1
                        shiftInfo =  b.xpath('a[@class="btn"]/@onclick')
                        if shiftInfo:
    #                         print '2222222222222',shiftInfo
                            shift = re.findall("('(.*)')", shiftInfo[0])
                            if shift: 
                                shiftid = shift[0][1]
                    else:
                        flag=0   
    
                item['flag'] = flag
                item['shiftid'] = shiftid
#                 print item
                yield  item     
                                   
            if nextPage>pageNo:
                url=response.url.split('?')[0]+'?pageNo=%s'%nextPage
                yield scrapy.FormRequest(url, formdata=payload, callback=self.parse_line, meta={"payload": payload,'item':item_bak})
                
            
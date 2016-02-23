# -*- coding: utf-8 -*-
import scrapy
import json
import datetime
import pypinyin
import re
from lxml import etree

from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter
from base import SpiderBase


class bus100Spider(SpiderBase):
    name = "bus100"
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
                              '450000': {"province_id": '450000', 'province_name': u"广西"},
                              '370000': {"province_id": '370000', 'province_name': u"山东"},
                              '210000': {"province_id": '210000', 'province_name': u"辽宁"},
                              '410000': {"province_id": '410000', 'province_name': u"河南"}
                              }
            crawl_province = crawl_province_dict.get(province_id)
        for province in provinceInfo[province_id]:
            cityId = province['cityId']
#             if province_id != "370000" or (province_id == "370000" and cityId in('370100')):
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
#         ports = [{'portName':'夏郢','pinyinPrefix':'rx'}]
        if ports:
            for port in ports:
                today = datetime.date.today()
                for i in range(0, 10):
                    sdate = str(today+datetime.timedelta(days=i))
                    if self.has_done(start["countyName"], port['portName'], sdate):
                        #self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                        continue
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
        if trainListInfo:
            start = response.meta["start"]
            end = response.meta["end"]
            crawl_province = response.meta["crawl_province"]
            crawl_city = response.meta["crawl_city"]
            payload = response.meta["payload"]
            sdate = payload['sendDate']
            item = LineItem()
            item['crawl_source'] = 'bus100'
            item['s_province'] = crawl_province['province_name']
            item['s_city_id'] = start['countyId']
            item['s_city_name'] = start['countyName']
            item['s_sta_id'] = start['countyId']
            start_short_name = start['pinyinPrefix']
            if not start_short_name or start_short_name == 'null':
                start_short_name = get_pinyin_first_litter(item['start_city_name'])
            item['s_city_code'] = start_short_name
            item['d_city_name'] = end['portName']
            d_city_code = end['pinyinPrefix']
            if not d_city_code:
                d_city_code = "".join(map(lambda x:x[0], pypinyin.pinyin(unicode(end['portName']), style=pypinyin.FIRST_LETTER)))
            item['drv_date'] = sdate
            item['d_city_code'] = d_city_code

            nextPage = int(trainListInfo['nextPage'])
            pageNo = int(trainListInfo['pageNo'])
    #                             print m['msg']
            sel = etree.HTML(trainListInfo['msg'])
            trains = sel.xpath('//div[@class="trainList"]')
            for n in trains:
                d_str = n.xpath("@data-list")[0]
                d_str = d_str[d_str.index("id=")+3:]
                shiftid = d_str[:d_str.index(",")]
                station = n.xpath('ul/li[@class="start"]/p/text()')
                time = n.xpath('ul/li[@class="time"]/p/strong/text()')
    #             print 'time->',time[0]
                banci = ''
                banci = n.xpath('ul/li[@class="time"]/p[@class="carNum"]/text()')
                if banci:
                    banci = banci[0].replace('\r\n', '').replace(' ',  '')
                else:
                    ord_banci = n.xpath('ul/li[@class="time"]/p[@class="banci"]/text()')
                    if ord_banci:
                        banci = ord_banci[0]
                price = n.xpath('ul/li[@class="price"]/strong/text()')
    #             print 'price->',price[0]
                infor = n.xpath('ul/li[@class="carriers"]/p[@class="info"]/text()')
                distance = ''
                if infor:
                    distance = infor[0].replace('\r\n', '').replace(' ',  '')
                buyInfo = n.xpath('ul/li[@class="buy"]')
                flag = 0
                for buy in buyInfo:
                    flag = buy.xpath('a[@class="btn"]/text()')   #判断可以买票
                    if flag:
                        flag = 1
                    else:
                        flag = 0
                item['drv_time'] = time[0]
                item['drv_datetime'] = datetime.datetime.strptime(sdate+' '+time[0], "%Y-%m-%d %H:%M")
                item['s_sta_name'] = station[0]
                item['d_sta_name'] = station[1]
                item['bus_num'] = banci.decode("utf-8").strip().rstrip(u"次")
                item["full_price"] = float(str(price[0]).split('￥')[-1])
                item["half_price"] = float(str(price[0]).split('￥')[-1])/2
                item['distance'] = distance
                item['shift_id'] = str(shiftid)
                item['crawl_datetime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                item['vehicle_type'] = ''
                item['seat_type'] = ''
                item['fee'] = 0
                item['left_tickets'] = 50 if flag else 0
                item['extra_info'] = {"flag": flag}
                yield item

            if nextPage > pageNo:
                url = 'http://84100.com/getBusShift/ajax'+'?pageNo=%s' % nextPage
                yield scrapy.FormRequest(url, formdata=payload, callback=self.parse_line,
                                         meta={"payload": payload, 'crawl_province':crawl_province,'crawl_city':crawl_city,'start':start, "end":end})
            elif nextPage and nextPage == pageNo:
                self.mark_done(start["countyName"], end['portName'], sdate)

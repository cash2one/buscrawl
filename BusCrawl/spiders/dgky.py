#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests
from lxml import etree
import random
import urllib
import urllib2
import cookielib
import re
import time
import math

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis, vcode_dgky
from BusCrawl.middleware import BrowserRandomUserAgentMiddleware
from scrapy.conf import settings
from pymongo import MongoClient


class DgkySpider(SpiderBase):
    name = "dgky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
#             'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
#             'BusCrawl.middleware.ProxyMiddleware': 410,
#             'BusCrawl.middleware.DgkyHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
       "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def query_code(self):
        cookies = {}
        code_url = 'http://www.mp0769.com/checkcode.asp'
        r = requests.get(code_url, headers=self.headers)
        code = vcode_dgky(r.content)
        if len(code) == 4:
            cookies.update(dict(r.cookies))
            self.cookies = cookies
            return code
        else:
            return self.query_code()

    def query_end_city(self, s_sta_name):
        if not hasattr(self, "_sta_dest_list"):
            self._sta_dest_list = {}

        if s_sta_name not in self._sta_dest_list:
            self._sta_dest_list[s_sta_name] = self.db.line.distinct('d_sta_name', {'crawl_source': 'gdsw', 's_sta_name': s_sta_name})
        result = self._sta_dest_list[s_sta_name]
        return result
    
    def start_requests(self):
#         code = self.query_code()
        db_config = settings.get("MONGODB_CONFIG")
        client = MongoClient(db_config["url"])
        self.db = client[db_config["db"]]
        ua = random.choice(BrowserRandomUserAgentMiddleware.user_agent_list)
        headers = {
               "User-Agent": ua,
               "Referer": "http://www.mp0769.com/",
               "Host": "www.mp0769.com",
               }
        self.headers = headers
        cj = cookielib.LWPCookieJar()
        cookie_support = urllib2.HTTPCookieProcessor(cj)
        opener = urllib2.build_opener(cookie_support, urllib2.HTTPHandler)
        urllib2.install_opener(opener)
        self.urllib2 = urllib2
        url = "http://www.mp0769.com/checkcode.asp?t="
        url = url+str(int(time.time()))
        req = self.urllib2.Request(url, headers=self.headers)
        result = self.urllib2.urlopen(req)
        code = ''
        
        station_dict = {
            "1901": ("东莞总站","东莞总站"),
            "1902": ("市客运北站","汽车北站"),
            "1903": ("市客运东站","东莞汽车东站"),
            "1904": ("东城汽车客运站","东城汽车站"),
            "1907": ("松山湖汽车客运站","松山湖汽车站"),
            "1908": ("长安客运站","长安汽车站"),
            "1909": ("虎门客运站","虎门汽车站"),
            "1911": ("厚街专线车站","厚街专线车站"),
            "1912": ("沙田汽车客运站","沙田汽车站"),
            "1916": ("石龙客运站","石龙车站"),
            "1917": ("石龙千里客运站","石龙千里车站"),
            "1919": ("桥头车站","桥头汽车站"),
            "1920": ("东坑车站","东坑汽车站"),
            "1925": ("石排客运站","石排客运站"),
            "1926": ("樟木头振通车站","振通客运站"),
            "1927": ("大朗汽车客运站","大朗汽车客运"),
            "1929": ("清溪客运站","清溪车站"),
            "1933": ("塘厦车站","塘厦客运站"),
            "1935": ("上沙汽车客运站","上沙汽车站"),
            "1930": ("凤岗客运站","凤岗车站"),

            }
        today = datetime.date.today()
        sdate = str(today+datetime.timedelta(days=1))
        init_url = "http://www.mp0769.com/bccx.asp?"
        for k, (dg_name, sw_name) in station_dict.items():
            if not self.is_need_crawl(city=dg_name):
                continue
#             dest_list = [u'石龙']
#             dest_list = self.get_dest_list("广东", '东莞')
            dest_list = self.query_end_city(sw_name)
            for y in dest_list:
                end = y.split("|")[0]
                today = datetime.date.today()
                for j in range(1, 7):
                    sdate = str(today+datetime.timedelta(days=j))
                    params = {
                     "action": "queryclick",
                     "Depot": k,
                     "date": sdate,
                     "Times": '',
                     "num":"1",
                     "Verifycode": code,
                     "tanchu": 1
                     }
                    init_url_param = "%s%s" % (init_url, urllib.urlencode(params))
                    station_url = init_url_param + '&station=%s' % json.dumps(end).replace('\u','%u')[1:-1]
                    form, sel = self.is_end_station(station_url)
                    if form:
                        yield scrapy.Request(station_url,
                                             method="GET",
                                             callback=self.parse_line,
                                             meta={'start_name': dg_name, 'sw_name': sw_name, 
                                                   'start_code': k, 'end': end, 'sdate':sdate})
                    else:
                        station = sel.xpath('//a')
                        for i in station:
                            td = i.xpath('font/text()')
                            href = i.xpath('@href')[0]
                            station_name = td[0].replace('\r\n','').replace('\t','').replace(' ',  '')
    #                         if station_name == end:
    #                             continue
                            station_url = "http://www.mp0769.com/cbprjdisp8.asp?"+href
                            form, sel = self.is_end_station(station_url)
                            if form:
                                yield scrapy.Request(station_url,
                                                     method="GET",
                                                     callback=self.parse_line,
                                                     meta={'start_name': dg_name, 'sw_name': sw_name, 
                                                           'start_code': k, 'end': end,'sdate':sdate})

    def is_end_station(self, station_url):
        req = self.urllib2.Request(station_url, headers=self.headers)
        result = self.urllib2.urlopen(req)
        content = result.read()
        content = content.decode('gbk')
        sel = etree.HTML(content) 
        form = sel.xpath('//form[@method="Post"]/@action')
        return form, sel
    
    def query_line_info_by_gdsw(self, start_station, end_station, bus_num, drv_datetime):
        result = self.db.line.find_one({'crawl_source': 'gdsw',
                                        's_sta_name': start_station,
                                        'd_sta_name': end_station,
                                        'drv_datetime': drv_datetime,
                                        'bus_num': bus_num
                                        })
        return result

    def parse_line(self, response):
        "解析班车"
        res = response.body.decode('gbk')
        start_name = response.meta["start_name"]
        sw_name = response.meta["sw_name"]
        start_code = response.meta["start_code"]
        end = response.meta["end"]
        sdate = response.meta["sdate"]
        sel = etree.HTML(res) 
        next_url = ''
        for i, j in enumerate(sel.xpath("//a/text()")):
            if j == '下一页':
                next_url = sel.xpath("//a/@href")[i]
#         countObj = re.findall("查询到(\d+)班", str(res))
#         if countObj:
#             count = countObj
#             page = int(math.ceil(count/10))
        form = sel.xpath('//form[@method="Post"]/@action')
        full_price = 0
        left_tickets = 0
        flag = False
        if form:
            sch = sel.xpath('//table[@width="600"]/tr')
            for i in sch[1:]:
                status = i.xpath('td[8]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                if status != '售票':
                    continue
                bus_num = i.xpath('td[1]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                drv_date = i.xpath('td[2]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                drv_date = dte.strftime(dte.strptime(drv_date, '%Y-%m-%d'),'%Y-%m-%d')
                drv_time = i.xpath('td[3]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                start_station = i.xpath('td[4]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                #end_station = i.xpath('td[5]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                distance = i.xpath('td[7]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                href = i.xpath('td[9]/div/a/@onclick')[0]
                if 'javascript:alert' in href:
                    continue
                if not flag:
                    for i in range(10):
                        param = {}
                        for s in href.split(";")[0][15:-1].split("?")[1].split("&"):
                            k, v = s.split("=")
                            param[k] = v.encode('gb2312')
                        query_url = "%s%s" % ('http://www.mp0769.com/orderlist.asp?', urllib.urlencode(param))
                        req = self.urllib2.Request(query_url, headers=self.headers)
                        result = self.urllib2.urlopen(req)
                        content = result.read()
                        res = content.decode('gbk')
                        if '非法操作' in res:
                            query_url = "http://www.mp0769.com/" + href.split(";")[0][15:-1]
                            req = self.urllib2.Request(query_url, headers=self.headers)
                            result = self.urllib2.urlopen(req)
                            content = result.read()
                            res = content.decode('gbk')
                        check_url = re.findall("window.location.href=(.*);", res)[0][1:-1]
                        check_url = "http://www.mp0769.com/" + check_url
                        param = {}
                        for s in check_url.split("?")[1].split("&"):
                            k, v = s.split("=")
                            param[k] = v.encode('gb2312')
                        order_url = "http://www.mp0769.com/orderlist.asp?"
                        order_url = "%s%s" % (order_url, urllib.urlencode(param))
                        req = self.urllib2.Request(order_url, headers=self.headers)
                        result = self.urllib2.urlopen(req)
                        content = result.read()
                        sel = etree.HTML(content)
                        params = {}
                        for s in sel.xpath("//form[@id='Form1']//input"):
                            k, v = s.xpath("@name"), s.xpath("@value")
                            if k:
                                k, v = k[0], v[0] if k else ""
                                params[k] = v.encode('gb2312')
                        if not params or int(params.get('ct_price', 0)) == 0:
                            end_station = params['ct_stname'].decode('gbk')
                        else:
                            print "ct_price ", params['ct_price']
                            full_price = params['ct_price']
                            left_tickets = params['ct_accnum']
                            end_station = params['ct_stname'].decode('gbk')
                            flag = True
                            break
                drv_datetime = dte.strptime("%s %s" % (drv_date, drv_time), "%Y-%m-%d %H:%M")
                if not flag:
                    result = self.query_line_info_by_gdsw(sw_name,end_station,bus_num,drv_datetime)
                    if result:
                        full_price = result['full_price']
                        left_tickets = result['left_tickets']
                        flag = True
                    else:
                        print 111111,sw_name,end_station,bus_num,drv_datetime
                        print 3333333,end
                attrs = dict(
                    s_province = u'广东',
                    s_city_name = u"东莞",
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(u"东莞"),
                    s_sta_name = start_station,
                    s_sta_id = start_code,
                    d_city_name = end,
                    d_city_code= get_pinyin_first_litter(end),
                    d_city_id = '',
                    d_sta_name = end_station,
                    d_sta_id = '',
                    drv_date = drv_date,
                    drv_time = drv_time,
                    drv_datetime = drv_datetime,
                    distance = distance,
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = bus_num,
                    full_price = float(full_price),
                    half_price = float(full_price)/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {"query_url":href},
                    left_tickets = left_tickets,
                    crawl_source = "dgky",
                    shift_id="",
                )
                yield LineItem(**attrs)
        if next_url:
            url = "http://www.mp0769.com/bccx.asp?"
            param = {}
            try:
                for s in next_url.split("?")[1].split("&"):
                    k, v = s.split("=")
                    param[k] = v.encode('gb2312')
                url = url + urllib.urlencode(param)
            except:
                print next_url
            yield scrapy.Request(url,
                                 method="GET",
                                 callback=self.parse_line,
                                 meta={'start_name': start_name, "sw_name": sw_name,
                                       'start_code': start_code, 'end': end, 'sdate':sdate})
        else:
            pass
            #self.mark_done(start, end, sdate)

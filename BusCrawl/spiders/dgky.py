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
        
    def start_requests(self):
#         code = self.query_code()
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
            "1901":"东莞总站",
#             "1902":"市客运北站",
#             "1903":"市客运东站",
#             "1904":"东城汽车客运站",
#             "1905":"东莞市南城汽车客运站",
#             "1906":"榴花车站",
#             "1907":"松山湖汽车客运站",
#             "1908":"长安客运站",
#             "1909":"虎门客运站",
#             "1910":"厚街汽车站",
#             "1911":"厚街专线车站",
#             "1912":"沙田汽车客运站",
#             "1915":"中堂客运站",
#             "1916":"石龙客运站",
#             "1917":"石龙千里客运站",
#             "1918":"常平客运站",
#             "1919":"桥头车站",
#             "1920":"东坑车站",
#             "1923":"樟木头客运站",
#             "1924":"横沥客运站",
#             "1925":"石排客运站",
#             "1926":"樟木头振通车站",
#             "1927":"大朗汽车客运站",
#             "1928":"道滘汽车客运站",
#             "1929":"清溪客运站",
#             "1930":"凤岗客运站",
#             "1931":"东莞市黄江汽车客运站",
#             "1932":"长安客运北站",
#             "1933":"塘厦车站",
#             "1934":"虎门北栅汽车客运站",
#             "1935":"上沙汽车客运站",
#             "1939":"洪梅车站",
#             "1930":"凤岗客运站",
#             "1998":"广东电信天翼客运通",
            }
        today = datetime.date.today()
        sdate = str(today+datetime.timedelta(days=2))
        init_url = "http://www.mp0769.com/bccx.asp?"
        for k, v in station_dict.items():
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
#             station_url = station_url + '&station=%s' % json.dumps(u'深圳龙华').replace('\u','%u')[1:-1]

            end_list = [u'广州']
            dest_list = self.get_dest_list("广东", '东莞')
            for y in dest_list:
                end = y.split("|")[0]
#             for end in end_list:
                station_url = init_url_param + '&station=%s' % json.dumps(end).replace('\u','%u')[1:-1]
                form, sel = self.is_end_station(station_url)
                if form:
                    yield scrapy.Request(station_url,
                                         method="GET",
                                         callback=self.parse_line,
                                         meta={'start': v, 'end': end,'sdate':sdate})
                else:
                    station = sel.xpath('//a')
                    for i in station:
                        td = i.xpath('font/text()')
                        station_name = td[0].replace('\r\n','').replace('\t','').replace(' ',  '')
                        if station_name == end:
                            continue
                        station_url = init_url_param + '&station=%s' % json.dumps(station_name).replace('\u','%u')[1:-1]
                        form, sel = self.is_end_station(station_url)
                        if form:
                            yield scrapy.Request(station_url,
                                                 method="GET",
                                                 callback=self.parse_line,
                                                 meta={'start': v, 'end': end,'sdate':sdate})

    def is_end_station(self, station_url):
        req = self.urllib2.Request(station_url, headers=self.headers)
        result = self.urllib2.urlopen(req)
        content = result.read()
        content = content.decode('gbk')
        sel = etree.HTML(content) 
        form = sel.xpath('//form[@method="Post"]/@action')
        return form, sel

    def parse_line(self, response):
        "解析班车"
        res = response.body.decode('gbk')
        start = response.meta["start"]
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
        if form:
            sch = sel.xpath('//table[@width="600"]/tr')
            for i in sch[1:]:
                status = i.xpath('td[8]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                if status != '售票':
                    continue
                bus_num = i.xpath('td[1]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                drv_date = i.xpath('td[2]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                drv_time = i.xpath('td[3]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                start_station = i.xpath('td[4]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                end_station = i.xpath('td[5]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                chexing = i.xpath('td[6]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                distance = i.xpath('td[7]/div/text()')[0].replace('\r\n', '').replace('\t',  '').replace(' ',  '')
                href = i.xpath('td[9]/div/a/@onclick')[0].split(";")
                query_url = "http://www.mp0769.com/" + href[0][15:-1]
                full_price = 0
                left_tickets = 0
                for i in range(50):
                    req = urllib2.Request(query_url, headers=self.headers)
                    result = urllib2.urlopen(req)
                    content = result.read()
                    res = content
                    check_url = re.findall("window.location.href=(.*);", res)[0][1:-1]
                    check_url = "http://www.mp0769.com/" + check_url
                    param = {}
                    for s in check_url.split("?")[1].split("&"):
                        k, v = s.split("=")
                        param[k] = v
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
                        continue
                    else:
                        print "ct_price ", params['ct_price']
                        full_price = params['ct_price']
                        left_tickets = params['ct_accnum']
                        end_station = params['ct_stname'].decode('gbk')
                        break
                attrs = dict(
                    s_province = u'广东',
                    s_city_name = u"东莞",
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(u"东莞"),
                    s_sta_name = start_station,
                    s_sta_id = '',
                    d_city_name = end,
                    d_city_code= get_pinyin_first_litter(end),
                    d_city_id = '',
                    d_sta_name = end_station,
                    d_sta_id = '',
                    drv_date = drv_date,
                    drv_time = drv_time,
                    drv_datetime = dte.strptime("%s %s" % (drv_date, drv_time), "%Y-%m-%d %H:%M"),
                    distance = distance,
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = bus_num,
                    full_price = float(full_price),
                    half_price = float(full_price)/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {"query_url":query_url},
                    left_tickets = left_tickets,
                    crawl_source = "dgky",
                    shift_id="",
                )
                yield LineItem(**attrs)
        if next_url:
            url = "http://www.mp0769.com/bccx.asp?"
            param = {}
            for s in next_url.split("?")[1].split("&"):
                k, v = s.split("=")
                param[k] = v.encode('gb2312')
            url = url + urllib.urlencode(param)
            yield scrapy.Request(url,
                                 method="GET",
                                 callback=self.parse_line,
                                 meta={'start': v, 'end': end, 'sdate':sdate})
        else:
            pass
            #self.mark_done(start, end, sdate)

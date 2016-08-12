#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests
import urllib

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis
from scrapy.conf import settings
from pymongo import MongoClient
from pypinyin import pinyin, lazy_pinyin

CITY_TO_STATION = {
       "唐山":[
            u'唐山东站',
#             u'唐山西站', 
#             u'迁西站', u'迁安站', u'南堡站', u'滦县站', u'滦南站',
#             u'乐亭站', u'海港站', u'古冶站', u'丰南站', u'丰润站', u'曹妃甸站', u'遵化站',
#             u'玉田站'
            ]
}


class HebkySpider(SpiderBase):
    name = "hebky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.HebkyHeaderMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.1,
#        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def get_init_dest_list_bak(self, start_info):
        province_list = ('吉林','辽宁', '河北','黑龙江','广东',"云南",'山西',
                         '山东','广西壮族自治','江西','河南','浙江','安徽',
                         '湖北','湖南',"贵州",'陕西','江苏','内蒙古自治',
                         "四川",'海南','山东','甘肃','青海','宁夏回族自治',
                         "新疆维吾尔自治",'西藏自治','贵州',
                         '福建')
        rds = get_redis()
        rds_key = "crawl:dest:hebky:%s" % start_info['name']
        dest_str = rds.get(rds_key)
        if not dest_str:
            lst = []
            letter = 'abcdefghijklmnopqrstuvwxyz'
            for i in letter:
                for j in letter:
                    query = i+j
                    target_url = 'http://60.2.147.28/com/yxd/pris/openapi/depotQueryByName.action'
                    data = {
                            "startCode": start_info['code'],
                            "isindexCity": "true",
                            "iststation": "1",
                            "InputStr": query,
                            "type": "2",
                            "name": start_info['name']
                          }
                    proxies = {
                        'http': 'http://192.168.1.51:8888',
                        'https': 'http://192.168.1.51:8888',
                        }
                    res = requests.post(target_url, data=data)
                    try:
                        res = res.json()
                    except Exception, e:
                        continue
                        print e
                    res_list = res['values']['resultList']
                    for m in res_list:
                        target_name = m['depotName'].strip()
                        if target_name.endswith('站') or '测试' in target_name or len(target_name) <2:
                            continue
                        if len(target_name) > 3:
                            if target_name.startswith(province_list):
                                for n in province_list:
                                    if target_name.startswith(n):
                                        target_name = target_name.replace(n, '')
                                        break
                        m['depotName'] = target_name
                        if m not in lst:
                            lst.append(m)
            dest_str = json.dumps(lst)
            rds.set(rds_key, dest_str)
        lst = json.loads(dest_str)
        return lst
    
    def get_init_dest_list(self, start_info):
        province_list = ('吉林','辽宁', '河北','黑龙江','广东',"云南",'山西',
                         '山东','广西壮族自治','江西','河南','浙江','安徽',
                         '湖北','湖南',"贵州",'陕西','江苏','内蒙古自治',
                         "四川",'海南','山东','甘肃','青海','宁夏回族自治',
                         "新疆维吾尔自治",'西藏自治','贵州')
        rds = get_redis()
        rds_key = "crawl:dest:hebky"
        dest_str = rds.get(rds_key)
        if not dest_str:
            target_url = "http://60.2.147.28//com/yxd/pris/wsgp/queryCity.action"
            data = {
                "flag": "false",
                "isArrive": "true",
                "isStart": "false",
                "isindexCity": "false",
                "iststation": "0",
                "startCode": start_info['code'],
                "tabLevel": '0',
                "zjm": '',
                }
            r = requests.post(target_url,
                              data=urllib.urlencode(data),
                              headers={"User-Agent": "Chrome", "Content-Type": "application/x-www-form-urlencoded"})
            res = r.json()
            lst = []
            if res['values']['ca']:
                for i in res['values']['ca'][0]:
                    tmp = {}
                    tmp['depotCode'] = i[0]
                    tmp['iststation'] = i[4]
                    if i[4] in ['0']:
                        continue
                    else:
                        tmp['depotName'] = i[1].strip(' ')
                    target_name = tmp['depotName']
#                     if target_name.endswith('站'):
#                         continue
#                     if '直辖' not in target_name:
#                         if not target_name or len(target_name) > 4:
#                             if target_name.startswith(province_list):
#                                 target_name1 = target_name
#                                 for j in province_list:
#                                     if target_name.startswith(j):
#                                         target_name = target_name.replace(j, '')
#                                         break
                    tmp['depotName'] = target_name
                    lst.append(tmp)
            dest_str = json.dumps(lst)
            rds.set(rds_key, dest_str)
        lst = json.loads(dest_str)
        return lst

    def query_start_predate(self, code):
        url = 'http://60.2.147.28/com/yxd/pris/openapi/queryPreDate.action'
        data = {
          "startDepotCode": code,
          }
        res = requests.post(url, data=data)
        res = res.json()
        predate = 0
        if res['akfAjaxResult'] != '0':
            predate = 0
        else:
            predate = res['values']['preDate']
        return predate

    def start_requests(self):
        start_url = "http://60.2.147.28/com/yxd/pris/openapi/queryStartStation.action"
        data = {}
        db_config = settings.get("MONGODB_CONFIG")
        client = MongoClient(db_config["url"])
        self.db = client[db_config["db"]]
        yield scrapy.FormRequest(start_url,
                                 method="POST",
                                 formdata=data,
                                 callback=self.parse_start_city)

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["akfAjaxResult"] != "0":
            self.logger.error("parse_start_city: Unexpected return, %s", res)
            return
        line_url = 'http://60.2.147.28/com/yxd/pris/openapi/queryAllTicket.action'
        all_start_list = []
        for i in res['values']['list']:
            for j in i['list']:
                all_start_list.append(j)
        for city_name, station_list in CITY_TO_STATION.iteritems():
            print city_name
            if not self.is_need_crawl(city=city_name):
                continue
            end_list = self.get_init_dest_list({'code':'ZD1302070179'})
            print len(end_list)
            for start in all_start_list:
                if start['name'] not in station_list:
                    continue
#                 dest_list = []
#                 dest_list = self.get_dest_list("河北", city_name, start[1])
                for end in end_list:
                    if '@' in end["depotCode"]:
                        arriveIsArea = '2'
                    else:
                        arriveIsArea = '0'
                    today = datetime.date.today()
                    for i in range(1, 2):
                        sdate = str(today+datetime.timedelta(days=i))
                        if self.has_done(start["name"], end["depotName"]+end['depotCode'], sdate):
                            self.logger.info("ignore %s ==> %s %s" % (start["name"], end["depotName"], sdate))
                            continue
                        data = {
                            "arrivalDepotCode": end['depotCode'],
                            "arriveIsArea": arriveIsArea,
                            "beginTime": sdate,
                            "startDepotCode": start['code'],
                            "startIsArea": "0",
                        }
                        yield scrapy.FormRequest(line_url,
                                                 method="POST",
                                                 formdata=data,
                                                 callback=self.parse_line,
                                                 meta={"start": start, "end": end,"city_name":city_name,
                                                       "date": sdate, 'arriveIsArea':arriveIsArea})
    
    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        city_name = response.meta["city_name"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        arriveIsArea = response.meta["arriveIsArea"]
        self.logger.info("finish %s ==> %s" % (start["name"], end["depotName"]))
        self.mark_done(start["name"], end["depotName"]+end['depotCode'], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if  res["values"]["resultList"]:
            print res["values"]["resultList"]
            print start["name"] ,end["depotName"]
        if res["akfAjaxResult"] != "0":
            #self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["city_name"], end["city_name"], res["header"])
            return
        for d in res["values"]["resultList"]:
            if d['stopFlag'] == '0':
                if float(d["fullPrice"]) < 10:
                    continue
                attrs = dict(
                    s_province = '河北',
                    s_city_name = city_name,
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(unicode(city_name)),
                    s_sta_name = d["startDepotName"],
                    s_sta_id = d["startDepotCode"],
                    d_city_name = end["depotName"],
                    d_city_code=get_pinyin_first_litter(end["depotName"]),
                    d_city_id = '',
                    d_sta_name = d["arrivalDepotName"],
                    d_sta_id = d["arrivalDepotCode"],
                    drv_date = d["departDate"],
                    drv_time = d["leaveTime"],
                    drv_datetime = dte.strptime("%s %s" % (d["departDate"], d["leaveTime"]), "%Y-%m-%d %H:%M"),
                    distance = "0",
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = d["busCode"],
                    full_price = float(d["fullPrice"]),
                    half_price = float(d["fullPrice"])/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {"busCodeType": d["busCodeType"], "regsName": d["regsName"], 
                                  "busCompanyCode": d["busCompanyCode"],"s_code": start['code'],
                                  'e_code':end['depotCode'],'arriveIsArea':arriveIsArea},
                    left_tickets = int(d["remainSeats"]),
                    crawl_source = "hebky",
                    shift_id="",
                )
                yield LineItem(**attrs)


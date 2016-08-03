#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis


class GzqcpSpider(SpiderBase):
    name = "gzqcp"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.GzqcpHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
#        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def get_dest_list(self, start_info):
        province_list = ('吉林','辽宁', '河北','黑龙江','广东',"云南",'山西',
                 '山东','广西壮族自治','江西','河南','浙江','安徽',
                 '湖北','湖南',"贵州",'陕西','江苏','内蒙古自治',
                 "四川",'海南','山东','甘肃','青海','宁夏回族自治',
                 "新疆维吾尔自治",'西藏自治','贵州','福建')
        rds = get_redis()
        dest_str = ''
        rds_key = "crawl:dest:gzqcp:%s" % start_info['name']
        dest_str = rds.get(rds_key)
#         if not dest_str:
#             dest_str = '[]'
#         lst = json.loads(dest_str)
#         return lst
        if not dest_str:
            lst = []
            letter = 'abcdefghijklmnopqrstuvwxyz'
            for i in letter:
                for j in letter:
                    query = i+j
                    target_url = 'http://www.gzsqcp.com/com/yxd/pris/openapi/depotQueryByName.action'
                    data = {
                            "startCode": start_info['code'],
                            "isindexCity": "true",
                            "iststation": "1",
                            "InputStr": query,
                            "type": "2",
                          }
                    proxies = {
                        'http': 'http://192.168.1.51:8888',
                        'https': 'http://192.168.1.51:8888',
                        }
#                     res = requests.post(target_url, data=data, proxies=proxies)
                    res = requests.post(target_url, data=data)
                    try:
                        res_lists = res.json()
                    except Exception, e:
                        print e
                    for j in res_lists['values']['resultList']:
                        if j['depotName'].endswith('站') or '测试' in j['depotName'] or '－' in j['depotName'] or 'pt' in j['depotName'] :
                            continue
                        target_name = j['depotName']
                        if len(target_name) > 3:
                            if target_name.startswith(province_list):
                                for k in province_list:
                                    if target_name.startswith(k):
                                        target_name = target_name.replace(k, '')
                                        break
                        j['depotName'] = target_name
                        if j not in lst:
                            lst.append(j)
            dest_str = json.dumps(lst)
            rds.set(rds_key, dest_str)
        lst = json.loads(dest_str)
        return lst
    
    def query_start_predate(self, start):
        url = 'http://www.gzsqcp.com/com/yxd/pris/openapi/queryPreDate.action'
        data = {
          "startDepotCode": start['code'],
          }
        proxies = {
            'http': 'http://192.168.1.51:8888',
            'https': 'http://192.168.1.51:8888',
        }
#         res = requests.post(url, data=data,proxies=proxies)
        res = requests.post(url, data=data)
        try:
            res = res.json()
        except:
            print 111111111111111111111111111111,start['code'],start['name']
        predate = 0
        if res['akfAjaxResult'] != '0':
            predate = 0
        else:
            predate = res['values']['preDate']
        return predate

    def start_requests(self):
        start_url = "http://www.gzsqcp.com/com/yxd/pris/openapi/cityQueryAll.action"
        yield scrapy.FormRequest(start_url,
                                 method="POST",
                                 formdata={},
                                 callback=self.parse_start_city)

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["akfAjaxResult"] != "0":
            self.logger.error("parse_start_city: Unexpected return, %s", res)
            return
        start_list = []
        end_list = []
        for i in res["values"]["list"]:
            for j in i['list']:
                start_list.append(j)
        line_url = 'http://www.gzsqcp.com/com/yxd/pris/openapi/queryAllTicket.action'
#         start_list = [{u'code': u'520100', u'name': u'贵阳'}]
#         for end in end_list:
#             if end['depotName'] == '遵义':
#                 print end
        start_list_bak = []
        for start in start_list:
            if not self.is_need_crawl(city=start['name']):
                continue
            preDate = self.query_start_predate(start)
            if not preDate:
                continue
            start_list_bak.append(start)
#             end_list = [
#                         {u'iststation': u'2', u'depotCode': u'1075@JYSYS', u'depotName': u'\u9075\u4e49'},
# #                         {u'iststation': u'2', u'depotCode': u'520301ZYA@gydsys', u'depotName': u'\u9075\u4e49'}
#                         ]
#             end_list = []
        print len(start_list_bak)
        for start in start_list_bak:
            end_list = self.get_dest_list(start)
            print 111111111, start['name'], len(end_list)
#             end_list= []
            for end in end_list:
#                 if end['iststation'] == "1":
#                     if end["depotName"].endswith(('市',"县","州")):
#                         print  end['depotCode'],end["depotName"]
                if '@' in end["depotCode"]:
                    arriveIsArea = '2'
                elif end['depotCode'] in ['520203LZA', '520382YAA']:
                    arriveIsArea = '0'
                else:
                    arriveIsArea = '1'
                today = datetime.date.today()
                for i in range(1, 1):
                    sdate = str(today+datetime.timedelta(days=i))
                    if self.has_done(start["name"], end["depotName"]+end['depotCode'], sdate):
                        self.logger.info("ignore %s ==> %s %s" % (start["name"], end["depotName"], sdate))
                        continue
                    data = {
                        "arrivalDepotCode": end['depotCode'],
                        "arriveIsArea": arriveIsArea,
                        "beginTime": sdate,
                        "startDepotCode": start['code'],
                        "startIsArea": "1",
                        "test": end["depotName"]
                    }
                    yield scrapy.FormRequest(line_url,
                                             method="POST",
                                             formdata=data,
                                             callback=self.parse_line,
                                             meta={"start": start, "end": end, "date": sdate,'arriveIsArea':arriveIsArea})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        arriveIsArea = response.meta["arriveIsArea"]
        self.logger.info("finish %s ==> %s" % (start["name"], end["depotName"]))
        self.mark_done(start["name"], end["depotName"]+end['depotCode'], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if res["akfAjaxResult"] != "0":
            #self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["city_name"], end["city_name"], res["header"])
            return
        if res["values"]["resultList"]:
            print res["values"]["resultList"]
        for d in res["values"]["resultList"]:
            if d['stopFlag'] == '0':
#                 if not self.is_internet(start['code'], d["busCompanyCode"]):
#                     continue
#                 if int(d["remainSeats"]) < 1:
#                     continue
                attrs = dict(
                    s_province = '贵州',
                    s_city_name = start["name"],
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(start["name"]),
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
                    extra_info = {"busCodeType": d["busCodeType"], "regsName": d["regsName"], "busCompanyCode": d["busCompanyCode"],
                                  "s_code": start["code"],'e_code':end['depotCode'],'arriveIsArea':arriveIsArea},
                    left_tickets = int(d["remainSeats"]),
                    crawl_source = "gzqcp",
                    shift_id="",
                )
                yield LineItem(**attrs)

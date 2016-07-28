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


class FjkySpider(SpiderBase):
    name = "fjky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.FjkyHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
#        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def query_start_predate(self, code):
        url = 'http://www.968980.cn/com/yxd/pris/openapi/queryPreDate.action'
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

    def get_dest_list(self, start_info):
        province_list = ('吉林','辽宁', '河北','黑龙江','广东',"云南",'山西',
                         '山东','广西壮族自治','江西','河南','浙江','安徽',
                         '湖北','湖南',"贵州",'陕西','江苏','内蒙古自治',
                         "四川",'海南','山东','甘肃','青海','宁夏回族自治',
                         "新疆维吾尔自治",'西藏自治','贵州')
        rds = get_redis()
        rds_key = "crawl:dest:fjky16"
        dest_str = rds.get(rds_key)
        if not dest_str:
            target_url = "http://www.968980.cn//com/yxd/pris/wsgp/queryCity.action"
            data = {
                "flag": "false",
                "isArrive": "true",
                "isStart": "false",
                "iststation": "1",
                "startCode": start_info['code'],
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
                    tmp['code'] = i[0]
                    if i[4] in ['1', '2']:
                        tmp['name'] = i[1].strip(' ')
                    else:
                        lev_list = i[3].split(' ')
                        if len(lev_list) < 3:
                            tmp['name'] = i[1].strip(' ')
                        else:
                            tmp['name'] = lev_list[-1].strip(')').strip(' ')
                            province = lev_list[0].strip('(').strip(' ')
                            if province == '福建省':
                                tmp['name'] = i[1].strip(' ')
                    target_name = tmp['name']
                    if target_name.endswith('站'):
                        continue
                    if '直辖' not in target_name:
                        if not target_name or len(target_name) > 4:
                            if target_name.startswith(province_list):
                                target_name1 = target_name
                                for j in province_list:
                                    if target_name.startswith(j):
                                        target_name = target_name.replace(j, '')
                                        break
                    tmp['name'] = target_name
                    if not tmp['name'].endswith(('市','县','州','区','旗')):
                        continue
                    lst.append(tmp)
            dest_str = json.dumps(lst)
            rds.set(rds_key, dest_str)
        lst = json.loads(dest_str)
        return lst

    def start_requests(self):
        start_url = "http://www.968980.cn/com/yxd/pris/openapi/cityQueryAll.action"
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
        for i in res['values']['list']:
            for j in i['list']:
                start_list.append(j)
        end_list = self.get_dest_list(start_list[0])
#         end_list=[]
#         start_list=[]
        line_url = 'http://www.968980.cn/com/yxd/pris/openapi/queryAllTicket.action'
        for start in start_list:
            if not self.is_need_crawl(city=start['name']):
                continue
#                 preDate = self.query_start_predate(start[0])
# #                 preDate = 0
#                 if preDate:
            for end in end_list:
#                 if self.is_end_city(start['name'], end):
                today = datetime.date.today()
                for j in range(1, 3):
                    sdate = str(today+datetime.timedelta(days=j))
                    if self.has_done(start['name'], end["name"], sdate):
                        self.logger.info("ignore %s ==> %s %s" % (start['name'], end["name"], sdate))
                        continue
                    data = {
                        "arrivalDepotCode": end['code'],
                        "beginTime": sdate,
                        "startName": unicode(start['name']),
                        "endName": unicode(end["name"]),
                        "startDepotCode": start['code']
                    }
                    yield scrapy.FormRequest(line_url,
                                             method="POST",
                                             formdata=data,
                                             callback=self.parse_line,
                                             meta={"start": start, "end": end, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        self.mark_done(start['name'], end["name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        if res["akfAjaxResult"] != "0":
            #self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["city_name"], end["city_name"], res["header"])
            return
        for d in res["values"]["resultList"]:
            if d['stopFlag'] == '0':
#                 if float(d["fullPrice"]) < 5 or int(d["remainSeats"]) < 2:
#                     continue
                attrs = dict(
                    s_province = '福建',
                    s_city_name = start['name'],
                    s_city_id = start['code'],
                    s_city_code= get_pinyin_first_litter(start['name']),
                    s_sta_name = d["startDepotName"],
                    s_sta_id = d["startDepotCode"],
                    d_city_name = end["name"],
                    d_city_code=get_pinyin_first_litter(end["name"]),
                    d_city_id = end['code'],
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
                    extra_info = {"busCodeType": d["busCodeType"], "regsName": d["regsName"], "busCompanyCode": d["busCompanyCode"],"s_code": start['code'],'e_code':end['code']},
                    left_tickets = int(d["remainSeats"]),
                    crawl_source = "fjky",
                    shift_id="",
                )
                yield LineItem(**attrs)


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
from scrapy.conf import settings
from pymongo import MongoClient


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
#        "DOWNLOAD_DELAY": 0.1,
       "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def query_all_end_station(self):
        r = get_redis()
        key = "hebky_end_station"
        end_station_list = r.get(key)
        if end_station_list:
            return end_station_list
        else:
            end_station_list = []
            letter = 'abcdefghijklmnopqrstuvwxyz'
            for i in letter:
                for j in letter:
                    query = i+j
                    end_station_url = 'http://60.2.147.28/com/yxd/pris/openapi/depotQueryByName.action'
                    data = {
                          "type": "2",
                          "InputStr": query,
                          }
                    res_lists = requests.post(end_station_url, data=data)
                    res_lists = res_lists.json()
                    for res_list in res_lists['values']['resultList']:
                        end_station_list.append(json.dumps(res_list))
            r.set(key, json.dumps(list(set(end_station_list))))
            r.expire(key, 2*24*60*60)
            end_station_list = r.get(key)
            if end_station_list:
                return end_station_list
        return end_station_list

    def is_end_city(self, start, end):
        db_config = settings.get("MONGODB_CONFIG")
        client = MongoClient(db_config["url"])
        db = client[db_config["db"]]
        s_sta_name = start[1]
        result = db.line.distinct('d_city_name', {'crawl_source': 'hebky', 's_sta_name':s_sta_name})
        if end['depotName'] not in result:
            return 0
        else:
            return 1

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
    
#     def start_requests(self):
#         start_url = "http://60.2.147.28/com/yxd/pris/openapi/cityQueryAll.action"
#         yield scrapy.FormRequest(start_url,
#                                  method="POST",
#                                  formdata={},
#                                  callback=self.parse_start_city)

    def start_requests(self):
        start_url = "http://www.hb96505.com//com/yxd/pris/wsgp/queryCity.action"
        data = {
            "flag": "true",
            "isArrive ": "false",
            "isStart": "true",
            "iststation": "1",
            "tabLevel": "2",
            "zjm": '',
            }
        yield scrapy.FormRequest(start_url,
                                 method="POST",
                                 formdata=data,
                                 callback=self.parse_start_city)

    def parse_start_city(self, response):
        res = json.loads(response.body)
        if res["akfAjaxResult"] != "0":
            self.logger.error("parse_start_city: Unexpected return, %s", res)
            return
        start_list = res['values']['ca'][0]
        start_name = []
        for i in res['values']['ca'][1]:
            if i not in start_name:
                start_name.append(i)
        start_dict = {}
        for i in start_name:
            start_dict[i[0]] = i[1].split(',')
        end_list = self.query_all_end_station()
        end_list = json.loads(end_list)
        print "end_station_list",len(end_list)
        line_url = 'http://60.2.147.28/com/yxd/pris/openapi/queryAllTicket.action'
        for k, v in start_dict.items():
            city_name = k
            if not self.is_need_crawl(city=city_name) or city_name in (u'保定', u'石家庄',u'唐山'):
                continue
            for i in v:
                start = start_list[int(i)]
                preDate = self.query_start_predate(start[0])
#                 preDate = 0
                if preDate:
                    for end in end_list:
                        end = json.loads(end)
                        if 1:#self.is_end_city(start, end):
                            today = datetime.date.today()
                            for i in range(0, min(int(preDate), 7)):
                                sdate = str(today+datetime.timedelta(days=i))
                                if self.has_done(start[1], end["depotName"], sdate):
            #                         self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
                                    continue
             
                                #{"depotCode":"ZD1309280006","depotName":"安陵"}
                                data = {
                                    "arrivalDepotCode": end['depotCode'],
                                    "beginTime": sdate,
                                    "startName": unicode(start[1]),
                                    "endName": unicode(end["depotName"]),
                                    "startDepotCode": start[0]
                                }
                                yield scrapy.FormRequest(line_url,
                                                         method="POST",
                                                         formdata=data,
                                                         callback=self.parse_line,
                                                         meta={"start": start, "city_name": city_name, "end": end, "date": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        city_name = response.meta["city_name"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        self.mark_done(start[1], end["depotName"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
#         if  res["values"]["resultList"]:
#             print res["values"]["resultList"]
#             print start["name"] ,end["depotName"]
        if res["akfAjaxResult"] != "0":
            #self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["city_name"], end["city_name"], res["header"])
            return
        for d in res["values"]["resultList"]:
            if d['stopFlag'] == '0':
                attrs = dict(
                    s_province = '河北',
                    s_city_name = city_name,
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(city_name),
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
                    extra_info = {"busCodeType": d["busCodeType"], "regsName": d["regsName"], "busCompanyCode": d["busCompanyCode"],"s_code": start[0],'e_code':end['depotCode']},
                    left_tickets = int(d["remainSeats"]),
                    crawl_source = "hebky",
                    shift_id="",
                )
                yield LineItem(**attrs)


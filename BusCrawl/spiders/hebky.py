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
                    end_station_url = 'http://60.2.147.28/com/yxd/pris/openapi/depotQueryByName.action'
                    data={
                          "type": "2",
                          "InputStr": i,
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
    
    def start_requests(self):
        start_url = "http://60.2.147.28/com/yxd/pris/openapi/cityQueryAll.action"
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
#         for i in res["values"]["endlist"]:
#             for j in i['list']:
#                 end_list.append(j)
        end_list = self.query_all_end_station()
        end_list = json.loads(end_list)
        print "end_station_list",len(end_list)
        print end_list[0]
        line_url = 'http://60.2.147.28/com/yxd/pris/openapi/queryAllTicket.action'

#         start_list = [{u'code': u'520221', u'name': u'水城县'}]
#         end_list = [{u'code': u'522400', u'name': u'毕节市'}]
#         end_list = [{"depotCode":"ZD1302090125","depotName":u"曾家湾"}]
        for start in start_list:
            for end in end_list:
                end = json.loads(end)
                today = datetime.date.today()
                for i in range(0, 1):
                    sdate = str(today+datetime.timedelta(days=i))
#                     if self.has_done(start["name"], end["depotName"], sdate):
# #                         self.logger.info("ignore %s ==> %s %s" % (start["city_name"], end["city_name"], sdate))
#                         continue

                    #{"depotCode":"ZD1309280006","depotName":"安陵"}
                    data = {
                        "arrivalDepotCode": end['depotCode'],
                        "beginTime": sdate,
                        "startName": unicode(start["name"]),
                        "endName": unicode(end["depotName"]),
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
#         self.mark_done(start["name"], end["name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        print res["values"]["resultList"]
        if res["akfAjaxResult"] != "0":
            #self.logger.error("parse_line: Unexpected return, %s, %s->%s, %s", sdate, start["city_name"], end["city_name"], res["header"])
            return
        for d in res["values"]["resultList"]:
#             if d['stopFlag'] == '0':
#                 if not self.is_internet(start['code'], d["busCompanyCode"]):
#                     continue
                attrs = dict(
                    s_province = '河北',
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
                    extra_info = {"busCodeType": d["busCodeType"], "regsName": d["regsName"], "busCompanyCode": d["busCompanyCode"],"s_code": start["code"],'e_code':end['depotCode']},
                    left_tickets = int(d["remainSeats"]),
                    crawl_source = "hebky",
                    shift_id="",
                )
                yield LineItem(**attrs)

    def is_internet(self, s_code, busCompanyCode):
        r = get_redis()
        key = "%s_%s" % (s_code, busCompanyCode)
        t = r.get(key)
        if t == '1':
            return True
        elif t == '0':
            return False
        else:
            data = {
                "startDepotCode": s_code,
                "busCompanyCode": busCompanyCode,
                }
            headers = {
                "User-Agent": "Dalvik/1.6.0 (Linux; U; Android 4.4.4; MI 4W MIUI/V7.1.3.0.KXDCNCK)",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }
            url = "http://www.gzsqcp.com/com/yxd/pris/wsgp/isInternet.action"
            res = requests.post(url, data=data, headers=headers)
            ret = res.json()
            result = ret['values']['result']
            r.set(key, result)
            r.expire(key, 10*60*60)
            if result == '1':
                return True
            elif result == '0':
                return False
        return True

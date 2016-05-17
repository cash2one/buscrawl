#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import urllib
import time

from datetime import datetime as dte
from collections import OrderedDict
from BusCrawl.item import LineItem
from BusCrawl.utils.tool import get_pinyin_first_litter, md5
from base import SpiderBase


class TongChengSpider(SpiderBase):
    name = "tongcheng_app"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            'BusCrawl.middleware.ProxyMiddleware': 410,
            'BusCrawl.middleware.TongChengHeaderMiddleware': 410,
        },
        #"DOWNLOAD_DELAY": 0.2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    base_url = "http://m.ctrip.com/restapi/busphp/app/index.php"

    def start_requests(self):
        # 这是个pc网页页面
        line_url = "http://tcmobileapi.17usoft.com/bus/QueryHandler.ashx"
        for name in ["苏州", "南京", "无锡", "常州", "南通", "张家港", "昆山", "吴江", "常熟", "太仓", "镇江", "宜兴", "江阴", "兴化", "盐城", "扬州", "连云港", "徐州", "宿迁"]:
            if not self.is_need_crawl(city=name):
                continue
            self.logger.info("start crawl city %s", name)
            start = {"name": name, "province": "江苏"}
            for s in self.get_dest_list(start["province"], start["name"]):
                name, code = s.split("|")
                end = {"name": name, "short_pinyin": code}
                self.logger.info("start %s ==> %s" % (start["name"], end["name"]))

                today = datetime.date.today()
                for i in range(self.start_day(), 8):
                    sdate = str(today + datetime.timedelta(days=i))
                    if self.has_done(start["name"], end["name"], sdate):
                        self.logger.info("ignore %s ==> %s %s" % (start["name"], end["name"], sdate))
                        continue
                    data = {
                        "departure": start["name"],
                        "destination": end["name"],
                        "dptDate": sdate,
                        "queryType": 1,
                        "subCategory": 0,
                        "page": 1,
                        "pageSize": 1025,
                        "hasCategory": 1,
                        "dptStation": "",
                        "arrStation": "",
                        "dptTimeSpan": 0
                    }
                    headers, body = self.get_post_templ("getbusschedule", data)
                    yield scrapy.Request(line_url,
                                         method="POST",
                                         headers=headers,
                                         body=body,
                                         callback=self.parse_line,
                                         meta={"start": start, "end": end, "sdate": sdate})


    def get_post_templ(self, service_name, data):
        stime = str(int(time.time()*1000))
        account_id = "c26b007f-c89e-431a-b8cc-493becbdd8a2"
        version = "20111128102912"
        s="AccountID=%s&ReqTime=%s&ServiceName=%s&Version=%s" % (account_id, stime, service_name, version)
        digital_sign = md5(s+"8874d8a8b8b391fbbd1a25bda6ecda11")
        params = OrderedDict()
        params["request"] = OrderedDict()
        s="""{"request":{"body":{"clientInfo":{"clientIp":"192.168.111.104","deviceId":"898fd52b362f6a9c","extend":"4^4.4.4,5^MI 4W,6^-1","mac":"14:f6:5a:b9:d1:4a","manufacturer":"Xiaomi","networkType":"wifi","pushInfo":"d//igwEhgBGCI2TG6lWqlK1bASX03rDfA3JbL/g8WWZAjh0HL+Xl4O6Gnz/Md0IMtK5xaQLx2gx0lrKjigw0va5kMl4fwRtaflQwB/JWvEE=","refId":"16359978","tag":"|^^0^1^91^0^|","versionNumber":"8.0.5","versionType":"android"},"isUserLogin":"1","password":"X8OreO1LsvFYfESF/pau4chTlTsG2LB9bSaTxbq2GYcesBmrBKgsb7bFy9F/K5AC","loginName":"17051322878"},"header":{"accountID":"c26b007f-c89e-431a-b8cc-493becbdd8a2","digitalSign":"d9f62ee2d12b65eca96e5f14f13ff733","reqTime":"1458673470243","serviceName":"Loginv2","version":"20111128102912"}}}"""
        params = {
            "request": {
                "body": {
                    "clientInfo": {
                        "clientIp": "192.168.111.104",
                        "deviceId": "898fd52b362f6a9c",
                        "extend": "4^4.4.4,5^MI 4W,6^-1",
                        "mac": "14:f6:5a:b9:d1:4a",
                        "manufacturer": "Xiaomi",
                        "networkType": "wifi",
                        "pushInfo": "d//igwEhgBGCI2TG6lWqlK1bASX03rDfA3JbL/g8WWZAjh0HL+Xl4O6Gnz/Md0IMtK5xaQLx2gx0lrKjigw0va5kMl4fwRtaflQwB/JWvEE=",
                        "refId": "16359978",
                        "tag": "|^^0^1^91^0^|",
                        "versionNumber": "8.0.5",
                        "versionType": "android",
                    },
                },
                "header": {
                    "accountID": account_id,
                    "digitalSign": digital_sign,
                    "reqTime": stime,
                    "serviceName": service_name,
                    "version": version,
                }
            }
        }
        params["request"]["body"].update(data)
        body = json.dumps(params)
        req_data = md5(body+"4957CA66-37C3-46CB-B26D-E3D9DCB51535")
        headers = {
            "secver": 5,
            "reqdata": req_data,
            "alisign": "ab88e5c9-0266-4526-872c-7a9e15ce78fd",
            "sxx": "f28c70d32017edb57cfe4d6fc1a9d5b2",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/2.5.0",
        }
        return headers, body


    def parse_line(self, response):
        "解析班车"
        try:
            res = json.loads(response.body)
        except Exception, e:
            self.logger.error("%s %s", response.body, e)
            return
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["name"], end["name"], sdate)
        res = res["response"]
        if int(res["header"]["rspCode"]) != 0:
            self.logger.error("parse_target_city: Unexpected return, %s, %s %s" % (res["header"], start["name"], end["name"]))
            return

        for d in res["body"]["schedule"]:
            if not d["canBooking"]:
                continue
            left_tickets = int(d["ticketLeft"])
            from_city = unicode(d["departure"])
            to_city = unicode(d["destination"])
            from_station = unicode(d["dptStation"])
            to_station = unicode(d["arrStation"])

            attrs = dict(
                s_province = start["province"],
                s_city_id = "",
                s_city_name = from_city,
                s_sta_name = from_station,
                s_city_code=get_pinyin_first_litter(from_city),
                s_sta_id=d.get("dptStationCode",""),
                d_city_name = to_city,
                d_city_id="",
                d_city_code=end["short_pinyin"],
                d_sta_id="",
                d_sta_name = to_station,
                drv_date = d["dptDate"],
                drv_time = d["dptTime"],
                drv_datetime = dte.strptime("%s %s" % (d["dptDate"], d["dptTime"]), "%Y-%m-%d %H:%M"),
                distance = unicode(d["distance"]),
                vehicle_type = d["coachType"],
                seat_type = "",
                bus_num = d["coachNo"],
                full_price = float(d["ticketPrice"]),
                half_price = float(d["ticketPrice"])/2,
                fee = float(d["ticketFee"]),
                crawl_datetime = dte.now(),
                extra_info = {},
                left_tickets = left_tickets,
                crawl_source = "tongcheng",
                shift_id="",
            )
            yield LineItem(**attrs)

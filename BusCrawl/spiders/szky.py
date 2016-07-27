#!/usr/bin/env python
# encoding: utf-8

import scrapy
import json
import datetime
import requests
import random
import urllib

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase
from BusCrawl.middleware import BrowserRandomUserAgentMiddleware

from BusCrawl.utils.tool import get_pinyin_first_litter
from BusCrawl.utils.tool import get_redis, trans_js_str, vcode_cqky
from scrapy.conf import settings
from pymongo import MongoClient


class SzkySpider(SpiderBase):
    name = "szky"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
#             'BusCrawl.middleware.MobileRandomUserAgentMiddleware': 400,
#             'BusCrawl.middleware.ProxyMiddleware': 410,
#             'BusCrawl.middleware.SzkyHeaderMiddleware': 410,
        },
#        "DOWNLOAD_DELAY": 0.1,
       "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def query_cookies(self, headers):
        cookies = {}
        valid_code = ''
        if not valid_code:
            login_form = "http://124.172.118.225/UserData/UserCmd.aspx"
            valid_url = "http://124.172.118.225/ValidateCode.aspx"
            r = requests.get(login_form, headers=headers, cookies=cookies)
            cookies.update(dict(r.cookies))
            for i in range(3):
                r = requests.get(valid_url, headers=headers, cookies=cookies)
                if "image" not in r.headers.get('content-type'):
                    self.modify(ip="")
                else:
                    break
            cookies.update(dict(r.cookies))
            valid_code = vcode_cqky(r.content)

        if valid_code:
            headers = {
                "User-Agent": headers.get("User-Agent", ""),
                "Referer": "http://124.172.118.225/User/Default.aspx",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
            params = {
                "loginID": 'a13267109876',
                "loginPwd": '123456',
                "getInfo": 1,
                "loginValid": valid_code,
                "cmd": "login",
            }
            login_url = "http://124.172.118.225/UserData/UserCmd.aspx"
            r = requests.post(login_url, data=urllib.urlencode(params), headers=headers, cookies=cookies)
            ret = json.loads(trans_js_str(r.content))
            success = ret.get("success", True)
            res = {}
            if success:     # 登陆成功
                cookies.update(dict(r.cookies))
                if ret["F_Code"] != 'a13267109876':
                    res.update({'status': 1})
                    return res
                res.update({'status': 0, 'cookies': cookies, 'valid_code':valid_code})
                return res
            else:
                res.update({'status': 1})
                return res

    def start_requests(self):
        headers = {"User-Agent": random.choice(BrowserRandomUserAgentMiddleware.user_agent_list)}
        for i in range(50):
            res = self.query_cookies(headers)
            if res.get('status', '') == 0:
                cookies = res.get('cookies')
                valid_code = res.get('valid_code')
                break
        if cookies:
            station_dict = {
                    "B1K003": ('福田汽车站','100101'),
                    "B1K002": ("罗湖汽车站","100301"),
                    "B1K004": ("南山汽车站",'100702'),
                    "B1K005": ("盐田汽车站",'100401'),
                    "B1K006": ("东湖客运站","100501"),
                    "B2K037": ("深圳北汽车站",'01'),
                    "B1K010": ("皇岗客运站",'100203'),
                    "B2K040": ("机场客运站","10005"),
                }
            end_list = []
            letter = 'abcdefghijklmnopqrstuvwxyz'
            for i in letter:
                query = i
#                 for j in letter:
#                     query = i+j
                end_list.append(query)
            line_url = 'http://124.172.118.225/UserData/MQCenterSale.aspx'
            headers.update({
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "Referer": "http://124.172.118.225/User/Default.aspx",
                        "X-Requested-With": "XMLHttpRequest",
                    })
            for k, (name, w_code) in station_dict.items():
                    dest_list = self.get_dest_list("广东", '深圳')
                    for d in dest_list:
                        name, code = d["name"], d["code"]
                        end = {"city_name": y, "city_code": get_pinyin_first_litter(y)}
                        today = datetime.date.today()
                        for j in range(1, 7):
                            sdate = str(today+datetime.timedelta(days=j))
                            if self.has_done(name, end['city_name'], sdate):
                                self.logger.info("ignore %s ==> %s %s" % (name,end['city_name'],sdate))
                                continue
                            data = {
                                "DstNode": end['city_name'],
                                "OpAddress": "-1",
                                "OpStation":  "-1",
                                "OperMode": '',
                                "SchCode": '',
                                "SchDate": sdate,
                                "SchTime": '',
                                'SeatType': '',
                                'StartStation':  k,
                                'WaitStationCode': w_code,
                                'cmd': "MQCenterGetClass",
                                'txtImgCode': valid_code,
                            }
    #                         proxies = {
    #                             'http': 'http://192.168.1.33:8888',
    #                             'https': 'http://192.168.1.33:8888',
    #                             }
    #                         r = requests.post(line_url, data=urllib.urlencode(data), headers=headers, cookies=cookies,proxies=proxies)
    #                         content = json.loads(trans_js_str(r.content))
    #                         yield self.parse_line(content)
                            yield scrapy.FormRequest(line_url,
                                                     method="POST",
                                                     cookies=cookies,
                                                     headers=headers,
                                                     formdata=data,
                                                     callback=self.parse_line,
                                                     meta={"start": name, "end": end, "date": sdate}
                                                    )

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end = response.meta["end"]
        sdate = response.meta["date"]
        self.mark_done(start, end['city_name'], sdate)
        res = json.loads(trans_js_str(response.body))
        for d in res["data"]:
            if d['SchStat'] == '1':
                attrs = dict(
                    s_province = u'广东',
                    s_city_name = u"深圳",
                    s_city_id = '',
                    s_city_code= get_pinyin_first_litter(u"深圳"),
                    s_sta_name = d["SchWaitStName"],
                    s_sta_id = d["SchStationCode"],
                    d_city_name = end['city_name'],
                    d_city_code=end['city_code'],
                    d_city_id = d['SchDstNode'],
                    d_sta_name = d["SchNodeName"],
                    d_sta_id = d["SchNodeCode"],
                    drv_date = d["SchDate"],
                    drv_time = d["orderbytime"],
                    drv_datetime = dte.strptime("%s %s" % (d["SchDate"], d["orderbytime"]), "%Y-%m-%d %H:%M"),
                    distance = "0",
                    vehicle_type = "",
                    seat_type = "",
                    bus_num = d["SchLocalCode"],
                    full_price = float(d["SchStdPrice"]),
                    half_price = float(d["SchStdPrice"])/2,
                    fee = 0,
                    crawl_datetime = dte.now(),
                    extra_info = {"raw_info": d},
                    left_tickets = int(d["SchTicketCount"]),
                    crawl_source = "szky",
                    shift_id="",
                )
                yield LineItem(**attrs)


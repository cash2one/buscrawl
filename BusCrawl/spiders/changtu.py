#!/usr/bin/env python
# encoding: utf-8
import scrapy
import json
import datetime
import urllib

from datetime import datetime as dte
from BusCrawl.item import LineItem
from base import SpiderBase

#所有的： http://www.changtu.com/open/getCityArr.htm?type=ticket&callback=jsonpcallback
START_LIST = [
    {"id": '390073', "name": '南京', "pinyin": 'nanjingshi', "short_pinyin": "nj", "province": "江苏"},
    {"id": '410283', "name": '苏州', "pinyin": 'suzhoushi', "short_pinyin": "sz", "province": "江苏"},
    {"id": '121679', "name": '南宁', "pinyin": 'nanningshi', "short_pinyin": "nn", "province": "广西"},
    {"id":'63', "name":'天津', "pinyin":'tianjinshi', "short_pinyin": "tj", "province": "天津"},

    # 山东
    {"id": '19', "name": '济南', "pinyin": 'jinanshi', "short_pinyin": "jn", "province": "山东"},
    {"id": '488392', "name": '淄博', "pinyin": 'ziboshi', "short_pinyin": "zb", "province": "山东"},
    {"id": '69', "name": '威海', "pinyin": 'weihaishi', "short_pinyin": "wh", "province": "山东"},
    {"id": '520163', "name": '临沂', "pinyin": 'linyishi', "short_pinyin": "ly", "province": "山东"},
    {"id": '499467', "name": '潍坊', "pinyin": 'weifangshi', "short_pinyin": "wf", "province": "山东"},
    {"id": '511968', "name": '泰安', "pinyin": 'taianshi', "short_pinyin":'ts', "province": "山东"},
    {"id": '516989', "name": '日照', "pinyin": 'rizhaoshi', "short_pinyin":'rz', "province": "山东"},
    {"id": '536931', "name": '滨州', "pinyin": 'binzhoushi', "short_pinyin":'bz', "province": "山东"},
    {"id": '525881', "name": '德州', "pinyin": 'dezhoushi', "short_pinyin":'dz', "province": "山东"},
    {"id": '563649', "name": '聊城', "pinyin": 'liaochengshi', "short_pinyin":'lc', "province": "山东"},

    # 湖南
    {"id": '352228', "name": '张家界', "pinyin": 'zhangjiajieshi', "short_pinyin":'zjj', "province": "湖南"},
    {"id": '375381', "name": '凤凰', "pinyin": 'fenghuangxian', "short_pinyin":'fh', "province": "湖南"},
    {"id": '366953', "name": '怀化', "pinyin": 'huaihuashi', "short_pinyin":'hh', "province": "湖南"},
    {"id": '361333', "name": '永州', "pinyin": 'yongzhoushi', "short_pinyin":'yz', "province": "湖南"},
]


class ChangtuSpider(SpiderBase):
    name = "changtu"
    custom_settings = {
        "ITEM_PIPELINES": {
            'BusCrawl.pipeline.MongoPipeline': 300,
        },

        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'BusCrawl.middleware.BrowserRandomUserAgentMiddleware': 400,
            #'BusCrawl.middleware.ChangtuProxyMiddleware': 410,
        },
        "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def start_requests(self):
        dest_url = "http://www.changtu.com/open/endBookCities.htm?cid=%s&s=%s&t=ticket"
        for d in START_LIST:
            if not self.is_need_crawl(province=d["province"], city=d["name"]):
                continue
            for i in range(97, 123):
                c = chr(i)
                url = dest_url % (d["id"], c)
                yield scrapy.Request(url,
                                    callback=self.parse_target_city,
                                    meta={"start": d})

    def parse_target_city(self, response):
        c = response.body
        c = c[c.index("["): c.rindex("]") + 1]
        for s in ["endId", "endName", "endPinyin", "endPinyinUrl", "stationMapIds", "endFirstLetterAll", "endCityNameDesc", "repeatFlag", "upEndName", "showName", "endTypeId", "provinceId", "provinceName"]:
            c=c.replace("%s:" % s, "\"%s\":" % s)
        c = c.replace("'", "\"")
        res = json.loads(c)

        line_url = "http://www.changtu.com/chepiao/querySchList.htm"
        start = response.meta["start"]
        days = 7
        if start["name"] == "张家界":
            days = 5
        for city in res:
            end = {
                "id": city["endId"],
                "name": city["showName"],
                "pinyin": city["endPinyinUrl"],
                "short_pinyin": city["endFirstLetterAll"],
                "end_type": city["endTypeId"],
            }

            today = datetime.date.today()
            for i in range(self.start_day(), days):
                sdate = str(today+datetime.timedelta(days=i))
                if self.has_done(start["name"], end["name"], sdate):
                    #self.logger.info("ignore %s ==> %s %s" % (start["name"], d["name"], sdate))
                    continue
                params = dict(
                    endTypeId=end["end_type"],
                    endId=end["id"],
                    planDate=sdate,
                    startCityUrl=start["pinyin"],
                    endCityUrl=end["pinyin"],
                    querySch=0,
                    startCityId=start["id"],
                    endCityId=end["id"],
                )
                yield scrapy.Request("%s?%s" % (line_url, urllib.urlencode(params)),
                                     callback=self.parse_line,
                                     meta={"start": start, "end": end, "sdate": sdate})

    def parse_line(self, response):
        "解析班车"
        start = response.meta["start"]
        end= response.meta["end"]
        sdate = response.meta["sdate"]
        self.mark_done(start["name"], end["name"], sdate)
        try:
            res = json.loads(response.body)
        except Exception, e:
            raise e
        self.logger.info("finish %s ==> %s" % (start["name"], end["name"]))
        # if res["bookFlag"] != "Y":
        #     #self.logger.error("parse_target_city: Unexpected return, %s" % res)
        #     return

        for d in res["schList"]:
            # if int(d["bookFlag"]) != 2:
            #     continue

            attrs = dict(
                s_province = start["province"],
                s_city_id = "%s|%s" % (start["id"], start["pinyin"]),
                s_city_name = start["name"],
                s_sta_name = d["localCarrayStaName"],
                s_city_code=start["short_pinyin"],
                s_sta_id=d["localCarrayStaId"],
                d_city_name = end["name"],
                d_city_id="%s|%s|%s" % (end["end_type"], end["pinyin"], end["id"]),
                d_city_code=end["short_pinyin"],
                d_sta_id=d.get("stopId", ""),
                d_sta_name=d["stopName"],
                drv_date=d["drvDate"],
                drv_time=d["drvTime"],
                drv_datetime = dte.strptime("%s %s" % (d["drvDate"], d["drvTime"]), "%Y-%m-%d %H:%M"),
                distance = unicode(d["mile"]),
                vehicle_type = d["busTypeName"],
                seat_type = "",
                bus_num = d["scheduleId"],
                full_price = float(d["fullPrice"]),
                half_price = float(d["fullPrice"])/2,
                fee = 0,
                crawl_datetime = dte.now(),
                extra_info = {"id": d["id"], "getModel": d["getModel"], "ticketTypeStr": d["ticketTypeStr"], "stationMapId": d["stationMapId"]},
                left_tickets = int(d["seatAmount"]),
                crawl_source = "changtu",
                shift_id="",
            )
            yield LineItem(**attrs)
